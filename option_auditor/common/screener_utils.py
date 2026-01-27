import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Callable, Dict, Any, Optional

from option_auditor.common.data_utils import (
    get_cached_market_data,
    fetch_batch_data_safe,
    prepare_data_for_ticker,
    _calculate_trend_breakout_date
)
from option_auditor.common.constants import SECTOR_COMPONENTS

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
        except:
            continue

    return filtered_list

def resolve_region_tickers(region: str) -> list:
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
        # S&P 500 (Volume Filtered) + Watch List
        # Note: We use check_trend=False to get the universe.
        sp500 = _get_filtered_sp500(check_trend=False)
        watch_list = SECTOR_COMPONENTS.get("WATCH", [])
        return list(set(sp500 + watch_list))
    else: # us / combined default
        all_tickers = []
        for t_list in SECTOR_COMPONENTS.values():
            all_tickers.extend(t_list)
        return list(set(all_tickers))

class ScreeningRunner:
    def __init__(self, ticker_list: Optional[List[str]] = None, time_frame: str = "1d", region: str = "us", check_mode: bool = False, workers: int = 4):
        self.ticker_list = ticker_list
        self.time_frame = time_frame
        self.region = region
        self.check_mode = check_mode
        self.workers = workers

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
