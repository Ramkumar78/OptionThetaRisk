import os
import csv
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, date
import logging
import time
import random
import numpy as np
from option_auditor.common.resilience import data_api_breaker, ResiliencyGuru

logger = logging.getLogger(__name__)

CACHE_DIR = "cache_data"

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Fix for yfinance TzCache permission issues in Docker
try:
    tz_cache_path = os.path.join(CACHE_DIR, "tk_cache")
    if not os.path.exists(tz_cache_path):
        os.makedirs(tz_cache_path, exist_ok=True)
    yf.set_tz_cache_location(tz_cache_path)
except Exception as e:
    logger.warning(f"Failed to set yfinance cache location: {e}")

# Hardcoded fallback exchange rates (approximate)
FALLBACK_RATES = {
    ("GBP", "USD"): 1.27,
    ("USD", "GBP"): 1 / 1.27,
    ("USD", "INR"): 83.50,
    ("INR", "USD"): 1 / 83.50,
    ("GBP", "INR"): 106.0,
    ("INR", "GBP"): 1 / 106.0,
    ("EUR", "USD"): 1.08,
    ("USD", "EUR"): 1 / 1.08
}

def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcasts floats to float32 to save 50% memory.
    """
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].astype('float32')
    return df

def save_atomic(df: pd.DataFrame, file_path: str):
    """
    Prevents race conditions (Reading while writing).
    Writes to .tmp then atomic swap.
    """
    tmp_path = f"{file_path}.tmp"
    try:
        # Optimize before save
        df = optimize_dataframe(df)
        df.to_parquet(tmp_path)
        # Atomic replace
        os.replace(tmp_path, file_path)
        logger.info(f"✅ Atomically saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed atomic save: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def get_cached_market_data(ticker_list: list = None, period="2y", cache_name="sp500", force_refresh: bool = False, lookup_only: bool = False):
    """
    Retrieves data from disk cache if valid (<24 hours for market scans).
    Uses atomic writes and memory optimization.
    """
    file_path = os.path.join(CACHE_DIR, f"{cache_name}.parquet")

    # Determine Validity Duration
    validity_hours = 24 if "market_scan" in cache_name else 4

    # Check if Cache Exists and Age
    file_exists = os.path.exists(file_path)
    file_age = None
    is_valid = False
    is_stale_but_usable = False

    if file_exists and not force_refresh:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_age = datetime.now() - mtime
            age_hours = file_age.total_seconds() / 3600

            if age_hours < validity_hours:
                is_valid = True
            elif age_hours < 48:
                # Stale but usable fallback
                is_stale_but_usable = True
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")

    # 1. Return Valid Cache
    if is_valid:
        try:
            logger.info(f"🚀 Loading {cache_name} from cache (Age: {file_age})...")
            return pd.read_parquet(file_path)
        except Exception:
            logger.warning("Cache corrupted, will re-download.")

    # 2. Return Stale Cache (if allowed and not forcing refresh)
    if is_stale_but_usable and not force_refresh:
        try:
            logger.warning(f"⚠️  Cache {cache_name} is stale ({file_age}). Returning to prevent timeout.")
            return pd.read_parquet(file_path)
        except Exception as e:
             logger.warning(f"Failed to read stale cache {cache_name}: {e}")

    # 3. Lookup Only Mode
    if lookup_only:
        if not force_refresh:
            return pd.DataFrame()

    # 4. Download Fresh
    if not ticker_list:
        logger.warning("No ticker list provided for download.")
        return pd.DataFrame()

    logger.info(f"⏳ Downloading fresh data for {len(ticker_list)} tickers (Chunked)...")

    # Detect Indian tickers for logging/tuning
    use_threads = True
    if ticker_list and len(ticker_list) > 0 and isinstance(ticker_list[0], str):
        first = ticker_list[0]
        if first.endswith('.NS') or first.endswith('.BO'):
             logger.info("🇮🇳 Indian tickers detected. Using chunking with sleep for safety.")
        elif any(first.endswith(s) for s in ['.L', '.AS', '.DE', '.PA', '.MC', '.MI', '.HE']):
             logger.info("🇬🇧/🇪🇺 UK/Euro tickers detected. Disabling threads to prevent connection drop.")
             use_threads = False
             
    # Use safe batch fetch
    all_data = fetch_batch_data_safe(ticker_list, period=period, interval="1d", chunk_size=30, threads=use_threads)

    # 5. Save Cache Atomically
    if not all_data.empty:
        save_atomic(all_data, file_path)

    return all_data

def fetch_data_with_retry(ticker, period="1y", interval="1d", auto_adjust=True, retries=3):
    """
    Fetches data from yfinance with exponential backoff retry logic.
    """
    for attempt in range(retries):
        try:
            # Wrap the actual network call with the breaker
            df = data_api_breaker.call(yf.download, ticker, period=period, interval=interval, progress=False, auto_adjust=auto_adjust)
            if not df.empty:
                return df
        except Exception as e:
            # Check if it is a potentially transient error or just no data
            logger.warning(f"Retry {attempt+1}/{retries} for {ticker} failed: {e}")
            # Fall through to sleep

        if attempt < retries - 1:
            sleep_time = (2 ** attempt) + random.random()
            time.sleep(sleep_time)

    return pd.DataFrame()

def fetch_batch_data_safe(tickers: list, period="1y", interval="1d", chunk_size=30, threads=True, raise_on_error=False) -> pd.DataFrame:
    """
    Downloads data for a list of tickers in chunks to avoid Rate Limiting.
    Returns a combined DataFrame or Empty DataFrame on total failure.
    """
    if not tickers:
        return pd.DataFrame()

    # Deduplicate
    unique_tickers = sorted(list(set(tickers)))
    chunks = [unique_tickers[i:i + chunk_size] for i in range(0, len(unique_tickers), chunk_size)]

    data_frames = []
    logger.info(f"Fetching {len(unique_tickers)} tickers in {len(chunks)} batches...")

    for i, chunk in enumerate(chunks):
        try:
            if i > 0:
                time.sleep(1.0 + random.random() * 0.5)

            batch = data_api_breaker.call(
                yf.download,
                chunk,
                period=period,
                interval=interval,
                group_by='ticker',
                progress=False,
                auto_adjust=True,
                threads=threads
            )

            if not batch.empty:
                data_frames.append(batch)

        except Exception as e:
            if raise_on_error:
                # If specifically requested, bubble up the error (e.g. for Auth/Rate Limit detection)
                raise e

            logger.error(f"Batch {i} download failed or Circuit Open: {e}")
            if data_api_breaker.current_state == 'open':
                logger.warning("Circuit breaker open during batch fetch. Aborting remaining batches.")
                break

    if not data_frames:
        return pd.DataFrame()

    try:
        if len(data_frames) == 1:
            return data_frames[0]
        else:
            return pd.concat(data_frames, axis=1)
    except Exception as e:
        logger.error(f"Failed to concat batches: {e}")
        return pd.DataFrame()

def prepare_data_for_ticker(ticker, data_source, time_frame, period, yf_interval, resample_rule, is_intraday):
    """Helper to prepare DataFrame for a single ticker."""
    df = pd.DataFrame()

    # Extract from batch if available
    if data_source is not None:
        if isinstance(data_source.columns, pd.MultiIndex):
            try:
                 # Check Level 1 (standard) or Level 0 (group_by='ticker')
                if ticker in data_source.columns.get_level_values(1):
                    df = data_source.xs(ticker, axis=1, level=1).copy()
                elif ticker in data_source.columns.get_level_values(0):
                    df = data_source.xs(ticker, axis=1, level=0).copy()
            except Exception as e:
                logger.debug(f"Error slicing multi-index for {ticker}: {e}")
        else:
             df = data_source.copy()

    # If empty, sequential fetch with retry
    if df.empty:
         df = fetch_data_with_retry(ticker, period=period, interval=yf_interval, auto_adjust=not is_intraday)

    # Clean NaNs
    df = df.dropna(how='all')
    if df.empty:
        return None

    # Flatten if needed
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.get_level_values(0)
        except Exception as e:
            logger.debug(f"Error flattening cols for {ticker}: {e}")

    # Resample if needed
    if resample_rule:
        agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
        try:
            df = df.resample(resample_rule).agg(agg_dict)
            df = df.dropna()
        except Exception as e:
            logger.error(f"Error resampling {ticker}: {e}")

    return df

def _calculate_trend_breakout_date(df: pd.DataFrame) -> str:
    """
    Calculates the start date of the current trend (ISA Logic: Breakout > 50d High, Exit < 20d Low).
    Returns "N/A" if not in a trend.
    """
    try:
        # Ensure we have enough data
        if df.empty or len(df) < 50: return "N/A"

        # Calculate indicators if missing
        # Work on a copy/slice to avoid modifying original if needed, but adding columns is fine
        subset = df.copy()

        if 'High_50' not in subset.columns:
            subset['High_50'] = subset['High'].rolling(50).max().shift(1)
        if 'Low_20' not in subset.columns:
            subset['Low_20'] = subset['Low'].rolling(20).min().shift(1)

        curr_close = subset['Close'].iloc[-1]
        low_20 = subset['Low_20'].iloc[-1]

        # Check if currently in a trend state
        # The ISA logic defines a trend as "Safe" if Close > Low_20.
        # If currently stopped out (Close <= Low_20), then no active trend.
        if pd.isna(curr_close) or pd.isna(low_20) or curr_close <= low_20:
            return "N/A"

        # Search backwards
        limit = min(len(subset), 400)
        subset = subset.iloc[-limit:]

        is_breakout = subset['Close'] >= subset['High_50']
        is_broken = subset['Close'] <= subset['Low_20']

        break_indices = subset.index[is_broken]
        last_break_idx = break_indices[-1] if not break_indices.empty else None

        breakout_indices = subset.index[is_breakout]

        if last_break_idx is not None:
             valid_breakouts = breakout_indices[breakout_indices > last_break_idx]
        else:
             valid_breakouts = breakout_indices

        if not valid_breakouts.empty:
             return valid_breakouts[0].strftime("%Y-%m-%d")

        return "N/A"
    except Exception:
        return "N/A"

def get_market_holidays(exchange: str) -> list[date]:
    """
    Returns a list of market holidays for the given exchange.
    Supports: 'LSE', 'NSE', 'NYSE'.
    """
    exchange = exchange.upper()

    # 2024-2025 Basic Holiday List (Approximate)
    # Ideally should use pandas_market_calendars, but using static list for simplicity/portability.

    holidays = []

    if exchange == 'NYSE':
        holidays = [
            date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 19), date(2024, 3, 29),
            date(2024, 5, 27), date(2024, 6, 19), date(2024, 7, 4), date(2024, 9, 2),
            date(2024, 11, 28), date(2024, 12, 25),
            date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
            date(2025, 5, 26), date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1),
            date(2025, 11, 27), date(2025, 12, 25)
        ]
    elif exchange == 'LSE':
        holidays = [
            date(2024, 1, 1), date(2024, 3, 29), date(2024, 4, 1), date(2024, 5, 6),
            date(2024, 5, 27), date(2024, 8, 26), date(2024, 12, 25), date(2024, 12, 26),
            date(2025, 1, 1), date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 5),
            date(2025, 5, 26), date(2025, 8, 25), date(2025, 12, 25), date(2025, 12, 26)
        ]
    elif exchange == 'NSE':
        # NSE Holidays are plentiful, adding major ones
        holidays = [
            date(2024, 1, 22), date(2024, 1, 26), date(2024, 3, 8), date(2024, 3, 25),
            date(2024, 3, 29), date(2024, 4, 11), date(2024, 4, 17), date(2024, 5, 1),
            date(2024, 6, 17), date(2024, 7, 17), date(2024, 8, 15), date(2024, 10, 2),
            date(2024, 11, 1), date(2024, 11, 15), date(2024, 12, 25),
            date(2025, 1, 26), date(2025, 2, 26), date(2025, 3, 14), date(2025, 3, 31),
            date(2025, 4, 10), date(2025, 4, 14), date(2025, 4, 18), date(2025, 5, 1),
            date(2025, 8, 15), date(2025, 8, 27), date(2025, 10, 2), date(2025, 10, 21),
            date(2025, 12, 25)
        ]

    return holidays

def get_currency_symbol(ticker: str) -> str:
    """
    Identifies the currency for a given ticker symbol.
    Logic:
      - .L -> GBP (Great British Pound)
      - .NS / .BO -> INR (Indian Rupee)
      - .AS, .DE, .PA, .MC, .MI, .HE -> EUR (Euro)
      - Default -> USD (US Dollar)
    """
    if not ticker:
        return "USD"

    ticker = ticker.upper()
    if ticker.endswith('.L'):
        return "GBP"
    if ticker.endswith('.NS') or ticker.endswith('.BO'):
        return "INR"
    if any(ticker.endswith(s) for s in ['.AS', '.DE', '.PA', '.MC', '.MI', '.HE']):
        return "EUR"

    return "USD"

def fetch_exchange_rate(from_curr: str, to_curr: str) -> float:
    """
    Fetches the exchange rate between two currencies.
    Uses yfinance for live rates (e.g. GBPUSD=X) with fallback to hardcoded constants.
    """
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()

    if from_curr == to_curr:
        return 1.0

    pair = (from_curr, to_curr)

    # Try fetching live rate
    ticker_map = {
        ("GBP", "USD"): "GBPUSD=X",
        ("EUR", "USD"): "EURUSD=X",
        ("INR", "USD"): "INR=X", # This is usually USDINR=X (USD to INR), so INR to USD is 1/USDINR
        ("USD", "INR"): "USDINR=X", # This returns how many INR per 1 USD
        ("USD", "GBP"): "GBP=X" # Usually implies inverse? yfinance logic varies.
    }

    # Direct yfinance lookup for standard pairs
    # Note: Yahoo Finance tickers are usually XXXYYY=X for "How many YYY per 1 XXX"
    yf_ticker = f"{from_curr}{to_curr}=X"

    try:
        # Check specific known mappings if generic construction fails or is ambiguous
        if from_curr == "USD" and to_curr == "INR":
            yf_ticker = "INR=X" # Wait, INR=X is usually USD/INR rate? Let's check standard.
            # Actually USDINR=X is standard.
            yf_ticker = "USDINR=X"

        data = yf.Ticker(yf_ticker)
        hist = data.history(period="1d")
        if not hist.empty:
            rate = hist['Close'].iloc[-1]
            logger.info(f"Fetched live rate for {from_curr}/{to_curr}: {rate}")
            return float(rate)
    except Exception as e:
        logger.debug(f"Live exchange rate fetch failed for {yf_ticker}: {e}")

    # Fallback
    if pair in FALLBACK_RATES:
        logger.info(f"Using fallback rate for {from_curr}/{to_curr}: {FALLBACK_RATES[pair]}")
        return FALLBACK_RATES[pair]

    # Inverse fallback
    inverse_pair = (to_curr, from_curr)
    if inverse_pair in FALLBACK_RATES:
        rate = 1.0 / FALLBACK_RATES[inverse_pair]
        logger.info(f"Using inverse fallback rate for {from_curr}/{to_curr}: {rate}")
        return rate

    logger.warning(f"No exchange rate found for {from_curr} -> {to_curr}. Assuming 1.0")
    return 1.0

def convert_currency(amount: float, from_curr: str, to_curr: str) -> float:
    """
    Converts an amount from one currency to another.
    """
    rate = fetch_exchange_rate(from_curr, to_curr)
    return amount * rate
