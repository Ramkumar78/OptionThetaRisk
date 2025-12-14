import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
import time
import random

logger = logging.getLogger(__name__)

CACHE_DIR = "cache_data"

def get_cached_market_data(ticker_list, period="2y", cache_name="sp500"):
    """
    Retrieves data from disk cache if valid (<4 hours old).
    Otherwise, downloads fresh data, saves it, and returns it.
    """
    # Ensure cache directory exists
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    file_path = os.path.join(CACHE_DIR, f"{cache_name}.parquet")

    # 1. Check if Cache is Valid
    is_valid = False
    if os.path.exists(file_path):
        try:
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_age < timedelta(hours=4): # Cache for 4 hours
                is_valid = True
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")

    # 2. FAST PATH: Return Cache
    if is_valid:
        try:
            logger.info(f"🚀 Loading {cache_name} from cache...")
            return pd.read_parquet(file_path)
        except Exception:
            logger.warning("Cache corrupted, re-downloading.")

    # 3. SLOW PATH: Download & Save
    logger.info(f"⏳ Downloading fresh data for {len(ticker_list)} tickers...")

    # Use safe batch fetch
    all_data = fetch_batch_data_safe(ticker_list, period=period, interval="1d", chunk_size=50)

    # 4. Save to Disk (The Fix)
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

def fetch_batch_data_safe(tickers: list, period="1y", interval="1d", chunk_size=50) -> pd.DataFrame:
    """
    Downloads data for a list of tickers in chunks to avoid Rate Limiting.
    Returns a combined DataFrame or Empty DataFrame on total failure.
    """
    if not tickers:
        return pd.DataFrame()

    # Deduplicate
    unique_tickers = list(set(tickers))
    chunks = [unique_tickers[i:i + chunk_size] for i in range(0, len(unique_tickers), chunk_size)]

    data_frames = []
    logger.info(f"Fetching {len(unique_tickers)} tickers in {len(chunks)} batches...")

    for i, chunk in enumerate(chunks):
        try:
            # Randomize sleep slightly to look more human if needed
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
                threads=True
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
