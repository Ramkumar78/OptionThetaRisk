import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
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
        except Exception:
             pass

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
            pass

        if attempt < retries - 1:
            sleep_time = (2 ** attempt) + random.random()
            time.sleep(sleep_time)

    return pd.DataFrame()

def fetch_batch_data_safe(tickers: list, period="1y", interval="1d", chunk_size=30, threads=True) -> pd.DataFrame:
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
                pass
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
            pass

    # Resample if needed
    if resample_rule:
        agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
        try:
            df = df.resample(resample_rule).agg(agg_dict)
            df = df.dropna()
        except Exception as e:
            logger.error(f"Error resampling {ticker}: {e}")
            pass

    return df
