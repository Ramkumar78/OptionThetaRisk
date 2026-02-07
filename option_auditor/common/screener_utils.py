import pandas as pd
import logging
import math
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Callable, Dict, Any, Optional
import yfinance as yf

from option_auditor.common.data_utils import (
    get_cached_market_data,
    fetch_batch_data_safe,
    prepare_data_for_ticker,
    _calculate_trend_breakout_date
)
from option_auditor.common.constants import SECTOR_COMPONENTS, TICKER_NAMES

from option_auditor.uk_stock_data import get_uk_tickers, get_uk_euro_tickers
from option_auditor.india_stock_data import get_indian_tickers
from option_auditor.us_stock_data import get_united_states_stocks
try:
    from option_auditor.sp500_data import get_sp500_tickers
except ImportError:
    def get_sp500_tickers(): return []

# Constants
DEFAULT_RSI_LENGTH = 14
DEFAULT_ATR_LENGTH = 14
DEFAULT_SMA_FAST = 50
DEFAULT_SMA_SLOW = 200
DEFAULT_EMA_FAST = 5
DEFAULT_EMA_MED = 13
DEFAULT_EMA_SLOW = 21
DEFAULT_DONCHIAN_WINDOW = 20

logger = logging.getLogger(__name__)

def _get_filtered_sp500(check_trend: bool = True) -> list:
    """
    Returns a filtered list of S&P 500 tickers based on Volume (>500k) and optionally Trend (>SMA200).
    """
    base_tickers = get_sp500_tickers()
    if not base_tickers:
        return []

    filtered_list = []

    # Use CACHED data to prevent timeouts and redundant downloads.
    # We use "market_scan_v1" which contains 2y data for S&P 500.
    # If the cache is missing, this will download it (heavy), but future calls will be instant.
    try:
        data = get_cached_market_data(base_tickers, period="2y", cache_name="market_scan_v1")
    except Exception as e:
        logger.error(f"Failed to get S&P 500 cache: {e}")
        data = pd.DataFrame()

    if data.empty:
        # Fallback to returning the base list if data unavailable, to allow scanning to proceed (albeit unfiltered)
        logger.warning("S&P 500 filter data unavailable. Returning raw list.")
        return base_tickers

    # Iterate through the downloaded data to check criteria
    # OPTIMIZED ITERATION
    if isinstance(data.columns, pd.MultiIndex):
        iterator = [(ticker, data[ticker]) for ticker in data.columns.unique(level=0)]
    else:
        # Fallback for single ticker result (rare)
        iterator = [(base_tickers[0], data)] if not data.empty and len(base_tickers)==1 else []

    for ticker, df in iterator:
        try:
             # CLEANUP: Drop the top level index to make it a standard OHLVC df
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)

            df = df.dropna(how='all')
            if len(df) < 20: continue

            # 1. Volume Filter (> 500k avg over last 20 days)
            if 'Volume' in df.columns:
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                if avg_vol < 500000: continue
            else:
                 continue

            # 2. Trend Filter (> SMA 200)
            if check_trend:
                if len(df) < 200: continue
                sma_200 = df['Close'].rolling(200).mean().iloc[-1]
                curr_price = df['Close'].iloc[-1]
                if curr_price < sma_200: continue

            filtered_list.append(ticker)
        except Exception as e:
            logger.warning(f"Error filtering S&P ticker {ticker}: {e}")
            continue

    return filtered_list

def resolve_region_tickers(region: str, check_trend: bool = False, only_watch: bool = False) -> list:
    """
    Helper to resolve ticker list based on region.
    Default: US (Sector Components + Watch)
    """
    if region == "uk_euro":
        return get_uk_euro_tickers()
    elif region == "uk":
        try:
            return get_uk_tickers()
        except ImportError:
            # Fallback to UK/Euro or empty
            return get_uk_euro_tickers()
    elif region == "united_states":
        return get_united_states_stocks()
    elif region == "india":
        return get_indian_tickers()
    elif region == "sp500":
        watch_list = SECTOR_COMPONENTS.get("WATCH", [])
        if only_watch:
            return watch_list
        # S&P 500 (Volume Filtered) + Watch List
        sp500 = _get_filtered_sp500(check_trend=check_trend)
        return list(set(sp500 + watch_list))
    else: # us / combined default
        all_tickers = []
        for t_list in SECTOR_COMPONENTS.values():
            all_tickers.extend(t_list)
        return list(set(all_tickers))

def resolve_ticker(query: str) -> str:
    """
    Resolves a query (Ticker or Company Name) to a valid ticker symbol.
    Uses TICKER_NAMES for lookup.
    """
    if not query: return ""
    query = query.strip().upper()

    if query in TICKER_NAMES:
        return query

    if "." not in query:
        if f"{query}.L" in TICKER_NAMES: return f"{query}.L"
        if f"{query}.NS" in TICKER_NAMES: return f"{query}.NS"

    for k, v in TICKER_NAMES.items():
        if v.upper() == query:
            return k

    for k, v in TICKER_NAMES.items():
        if query in v.upper():
            return k

    return query

def sanitize(val):
    """
    Converts NaN, Infinity, and -Infinity to None (JSON null).
    Also converts numpy floats to standard Python floats.
    This prevents the 'Out of range float values are not JSON compliant' error.
    """
    try:
        if val is None: return None
        # Handle numpy types and standard floats
        if isinstance(val, (float, np.floating)):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val) # Force conversion to python float
        return val
    except:
        return None

class ScreeningRunner:
    def __init__(self, ticker_list: Optional[List[str]] = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False, workers: int = 4, data_period: str = None):
        self.ticker_list = ticker_list
        self.time_frame = time_frame
        self.region = region
        self.check_mode = check_mode
        self.workers = workers
        self.custom_period = data_period

        # Determine intervals and periods
        self.yf_interval = "1d"
        self.resample_rule = None
        self.is_intraday = False
        self.period = "1y" # Default

        self._configure_timeframe()

    def _configure_timeframe(self):
        if self.time_frame == "49m":
            self.yf_interval = "5m"
            self.resample_rule = "49min"
            self.is_intraday = True
            self.period = "1mo"
        elif self.time_frame == "98m":
            self.yf_interval = "5m"
            self.resample_rule = "98min"
            self.is_intraday = True
            self.period = "1mo"
        elif self.time_frame == "196m":
            self.yf_interval = "5m"
            self.resample_rule = "196min"
            self.is_intraday = True
            self.period = "1mo"
        elif self.time_frame == "1wk":
            self.yf_interval = "1wk"
            self.period = "2y"
            self.is_intraday = False
        elif self.time_frame == "1mo":
            self.yf_interval = "1mo"
            self.period = "5y"
            self.is_intraday = False
        elif self.time_frame == "1h":
            self.yf_interval = "1h"
            self.period = "60d"
            self.is_intraday = True
        elif self.time_frame == "4h":
            self.yf_interval = "1h"
            self.resample_rule = "4h"
            self.is_intraday = True
            self.period = "60d"
        elif self.time_frame == "15m":
            self.yf_interval = "15m"
            self.period = "1mo"
            self.is_intraday = True
        elif self.time_frame == "5m":
             self.yf_interval = "5m"
             self.period = "5d"
             self.is_intraday = True
        elif self.time_frame == "1d":
            self.yf_interval = "1d"
            self.period = "2y" # Safe default for most daily strategies (e.g. 200 SMA)
            self.is_intraday = False

        if self.custom_period:
            self.period = self.custom_period

    def _fetch_data(self, tickers: List[str]) -> pd.DataFrame:
        data = None
        # Try Cache first for Daily/Weekly
        if not self.is_intraday and not self.check_mode:
            cache_name = "market_scan_v1"
            if self.region == "uk": cache_name = "market_scan_uk"
            elif self.region == "india": cache_name = "market_scan_india"
            elif self.region == "uk_euro": cache_name = "market_scan_europe"

            try:
                # Optimization: Check Master Cache coverage
                if len(tickers) > 50:
                     cached = get_cached_market_data(None, cache_name=cache_name, lookup_only=True)
                     if not cached.empty:
                         if isinstance(cached.columns, pd.MultiIndex):
                             available = cached.columns.levels[0]
                             intersection = len(set(tickers).intersection(available))
                             if intersection / len(tickers) > 0.6: # 60% coverage enough to prefer cache
                                 data = get_cached_market_data(tickers, period="2y", cache_name=cache_name)
            except Exception as e:
                logger.error(f"Cache check failed: {e}")

        # Fetch Live if no cache or cache failed or intraday
        if data is None:
            try:
                data = fetch_batch_data_safe(tickers, period=self.period, interval=self.yf_interval)
            except Exception as e:
                logger.error(f"Failed to bulk download: {e}")
                data = pd.DataFrame()

        return data

    def run(self, strategy_func: Callable[[str, pd.DataFrame], Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if self.ticker_list is None:
            self.ticker_list = resolve_region_tickers(self.region)

        # Apply ETF resolution if needed?
        # Generally resolve_region_tickers handles lists.
        # But if the user passed a list, we use it.

        if not self.ticker_list:
            return []

        data = self._fetch_data(self.ticker_list)

        results = []

        # Handle Flat vs MultiIndex
        # We need a map of ticker -> DataFrame
        ticker_data_map = {}

        if isinstance(data.columns, pd.MultiIndex):
            # Iterate Level 0
            for t in data.columns.levels[0]:
                if t in self.ticker_list:
                     ticker_data_map[t] = data[t] # This is a slice, might need copy inside strategy
        else:
            # Flat
            if len(self.ticker_list) == 1 and not data.empty:
                ticker_data_map[self.ticker_list[0]] = data
            elif not data.empty:
                 # Ambiguous. If we asked for many and got flat, it's weird.
                 # Maybe only 1 valid?
                 pass

        # If data fetch failed, we might still want to try one-by-one inside the thread (prepare_data_for_ticker handles fallback)
        # So even if ticker_data_map is empty, we proceed with ticker_list

        def _worker(ticker):
            # If we have batch data, pass it. If not, pass None and prepare_data_for_ticker will fetch.
            # But wait, prepare_data_for_ticker takes `data_source`.
            # If we pass None, it fetches.

            # The issue: If we pass the WHOLE batch data to every thread, it's slow/memory heavy if not sliced?
            # Or prepare_data_for_ticker expects the FULL batch and slices it itself?
            # Let's check prepare_data_for_ticker signature.
            # prepare_data_for_ticker(ticker, data_source, time_frame, period, yf_interval, resample_rule, is_intraday)

            # It expects `data_source` to be the batch DF.
            # So we should pass `data` (the full DF) to it?
            # `prepare_data_for_ticker` does:
            # if isinstance(data_source.columns, pd.MultiIndex): ... slice ...

            # So yes, we can pass `data` directly.

            try:
                # We use the shared helper to get the specific DF
                df = prepare_data_for_ticker(
                    ticker,
                    data,
                    self.time_frame,
                    self.period,
                    self.yf_interval,
                    self.resample_rule,
                    self.is_intraday
                )

                if df is None or df.empty:
                    return None

                # Run strategy
                return strategy_func(ticker, df)

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                return None

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_symbol = {executor.submit(_worker, sym): sym for sym in self.ticker_list}
            for future in as_completed(future_to_symbol):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    logger.error(f"Thread error: {e}")

        return results


def _norm_cdf(x):
    """
    Cumulative Distribution Function for Standard Normal Distribution.
    Using approximation (Error < 7.5e-8).
    """
    # If x > 6 or < -6, result is 1 or 0 respectively (to avoid overflow/useless calc)
    if x > 6.0: return 1.0
    if x < -6.0: return 0.0

    b1 =  0.319381530
    b2 = -0.356563782
    b3 =  1.781477937
    b4 = -1.821255978
    b5 =  1.330274429
    p  =  0.2316419

    c2 =  0.39894228

    a = abs(x)
    t = 1.0 / (1.0 + a * p)
    b = c2 * math.exp((-x * x) / 2.0)
    n = ((((b5 * t + b4) * t + b3) * t + b2) * t + b1) * t
    n = 1.0 - b * n
    if x < 0:
        n = 1.0 - n
    return n


def _calculate_put_delta(S, K, T, r, sigma):
    """
    Estimates Put Delta using Black-Scholes.
    S: Spot Price, K: Strike, T: Time to Exp (Years), r: Risk Free Rate, sigma: IV
    """
    if T <= 0 or sigma <= 0: return -0.5
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1) - 1.0

def _get_market_regime():
    """
    Fetches VIX to determine market regime.
    Returns current VIX level.
    """
    try:
        # 5 day history to get a smoothing or just last close
        vix = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
        if not vix.empty:
            return float(vix['Close'].iloc[-1])
    except Exception as e:
        logger.warning(f"Failed to fetch VIX: {e}")
    return 15.0 # Safe default

def run_screening_strategy(
    strategy_class: Callable,
    ticker_list: Optional[List[str]] = None,
    time_frame: str = "1d",
    region: str = "us",
    check_mode: bool = False,
    sorting_key: Optional[Callable] = None,
    reverse_sort: bool = False,
    data_period: str = None,
    **strategy_kwargs
) -> List[Dict[str, Any]]:
    """
    Generic runner for class-based strategies.
    Instantiates the strategy class for each ticker and runs .analyze().
    """
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode, data_period=data_period)

    def strategy_wrapper(ticker, df):
        try:
             # Try passing check_mode and kwargs
             return strategy_class(ticker, df, check_mode=check_mode, **strategy_kwargs).analyze()
        except TypeError:
             try:
                 # Try passing just kwargs (some don't take check_mode)
                 return strategy_class(ticker, df, **strategy_kwargs).analyze()
             except TypeError:
                  # Fallback: Try passing ONLY ticker and df (no kwargs support?)
                  return strategy_class(ticker, df).analyze()

    results = runner.run(strategy_wrapper)

    if sorting_key:
        results.sort(key=sorting_key, reverse=reverse_sort)

    return results
