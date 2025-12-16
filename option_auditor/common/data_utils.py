import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
import time
import random

logger = logging.getLogger(__name__)

CACHE_DIR = "cache_data"

# Fix for yfinance TzCache permission issues in Docker
try:
    tz_cache_path = os.path.join(CACHE_DIR, "tk_cache")
    if not os.path.exists(tz_cache_path):
        os.makedirs(tz_cache_path, exist_ok=True)
    yf.set_tz_cache_location(tz_cache_path)
except Exception as e:
    logger.warning(f"Failed to set yfinance cache location: {e}")

def get_cached_market_data(ticker_list: list = None, period="2y", cache_name="sp500", force_refresh: bool = False, lookup_only: bool = False):
    """
    Retrieves data from disk cache if valid (<24 hours for market scans).

    Args:
        ticker_list: List of tickers to download if cache is missing.
        period: Data period (e.g. "2y").
        cache_name: Filename for the cache.
        force_refresh: If True, ignore cache and re-download.
        lookup_only: If True, do NOT download if cache is missing/invalid. Return empty DataFrame.
                     Useful for screeners checking if "master" data is available.
    """
    # Ensure cache directory exists
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    file_path = os.path.join(CACHE_DIR, f"{cache_name}.parquet")

    # Determine Validity Duration
    # For heavy market scans (S&P 500), we allow 24 hours validity to prevent timeouts.
    # For smaller lists, 4 hours is fine.
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

            if file_age < timedelta(hours=validity_hours):
                is_valid = True
            elif file_age < timedelta(hours=48):
                # If cache is between 24h and 48h old, we consider it "stale but usable"
                # to prevent blocking the user with a massive download (Timeout).
                # The background worker should eventually refresh it.
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

    # 2. Return Stale Cache (if allowed)
    if is_stale_but_usable and not force_refresh:
        try:
            logger.warning(f"⚠️  Cache {cache_name} is stale ({file_age}). Returning to prevent timeout.")
            return pd.read_parquet(file_path)
        except Exception:
             pass

    # 3. Lookup Only Mode
    if lookup_only:
        # If we reached here, cache is missing or too old (>48h) or force_refresh is True (which shouldn't happen with lookup_only usually)
        # But if force_refresh is True, we proceed to download.
        # If force_refresh is False, we return empty.
        if not force_refresh:
            return pd.DataFrame()

    # 4. SLOW PATH: Download & Save
    if not ticker_list:
        logger.warning("No ticker list provided for download.")
        return pd.DataFrame()

    logger.info(f"⏳ Downloading fresh data for {len(ticker_list)} tickers (Chunked)...")

    # Detect Indian tickers for logging/tuning
    use_threads = True
    if ticker_list and len(ticker_list) > 0 and isinstance(ticker_list[0], str):
        if ticker_list[0].endswith('.NS') or ticker_list[0].endswith('.BO'):
             logger.info("🇮🇳 Indian tickers detected. Using chunking with sleep for safety.")
             # Optionally set use_threads = False if needed, but current sleep seems sufficient.
             
    # Use safe batch fetch
    # Chunk size reduced to 30 to prevent timeouts
    all_data = fetch_batch_data_safe(ticker_list, period=period, interval="1d", chunk_size=30, threads=use_threads)

    # 5. Save to Disk
    if not all_data.empty:
        try:
            all_data.to_parquet(file_path)
            logger.info(f"✅ Saved {cache_name} to disk.")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    return all_data

def fetch_data_with_retry(ticker, period="1y", interval="1d", auto_adjust=True, retries=3):
    """
    Fetches data from yfinance with exponential backoff retry logic.
    """
    for attempt in range(retries):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=auto_adjust)
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
            # Randomize sleep slightly to look more human if needed
            # For India/NSE, a sleep is critical.
            if i > 0:
                time.sleep(1.0 + random.random() * 0.5)

            # yf.download can be flaky, try/except the batch
            batch = yf.download(
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
            logger.error(f"Batch {i} download failed: {e}")

    if not data_frames:
        return pd.DataFrame()

    try:
        if len(data_frames) == 1:
            return data_frames[0]
        else:
            # axis=1 because yfinance returns columns like (Price, Ticker) with group_by='ticker'
            # Wait, when group_by='ticker', column levels are (Ticker, Price).
            # If we concat multiple batches, we are appending new tickers (columns).
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
