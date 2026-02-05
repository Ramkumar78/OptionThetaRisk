import logging
import pandas as pd
import yfinance as yf
from typing import List, Dict, Union

logger = logging.getLogger(__name__)

def normalize_ticker(broker_symbol: str) -> str:
    """Maps broker symbols to yfinance tickers."""
    if not isinstance(broker_symbol, str):
        return str(broker_symbol)
    s = broker_symbol.upper().strip()

    # Map common Indices
    index_map = {
        "SPX": "^SPX", "VIX": "^VIX", "DJX": "^DJI", "NDX": "^NDX", "RUT": "^RUT"
    }
    if s in index_map:
        return index_map[s]

    # Map Futures (Tastytrade uses /ES, Yahoo uses ES=F)
    if s.startswith("/"):
        return f"{s[1:]}=F"

    # Map Classes (BRK/B -> BRK-B)
    if "/" in s:
        return s.replace("/", "-")

    return s

def fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
    """
    Fetches live prices for a list of symbols using yfinance.
    Returns a dictionary mapping symbol -> current_price.
    Optimized to use batch downloading to prevent timeouts.
    """
    if not symbols:
        return {}

    # Filter out empty or non-string symbols
    valid_symbols = [s for s in symbols if isinstance(s, str) and s]
    if not valid_symbols:
        return {}

    # Deduplicate
    unique_symbols = list(set(valid_symbols))
    price_map = {}

    try:
        # Batch download "Last Price" (Close) for all tickers
        # period="1d" gives us the most recent day's data
        # group_by='ticker' ensures we can handle multiple tickers cleanly
        # threads=True for parallel fetching
        # auto_adjust=True to suppress warnings and get adjusted close
        # timeout=20 to ensure we don't hang forever

        # Note: yf.download returns a MultiIndex DataFrame if multiple tickers are passed
        # Columns: (Price, Ticker) or (Ticker, Price) if group_by='ticker'

        # If only 1 symbol, it returns a simple DataFrame
        # We handle both cases.

        if len(unique_symbols) == 1:
            sym = unique_symbols[0]
            df = yf.download(sym, period="1d", progress=False, auto_adjust=True)
            if not df.empty:
                # Handle potential MultiIndex return from yfinance even for single ticker
                close_val = df["Close"].iloc[-1]
                if isinstance(close_val, pd.Series):
                    price = float(close_val.iloc[0])
                else:
                    price = float(close_val)
                price_map[sym] = price
        else:
            # Batch
            tickers_str = " ".join(unique_symbols)
            df = yf.download(tickers_str, period="1d", group_by='ticker', threads=True, progress=False, auto_adjust=True)

            for sym in unique_symbols:
                try:
                    # Check if symbol is in columns
                    if sym in df.columns.levels[0]:
                        sym_df = df[sym]
                        # Drop NaNs to find valid data
                        sym_df = sym_df.dropna(how='all')
                        if not sym_df.empty:
                            # Get last close
                            close_val = sym_df["Close"].iloc[-1]
                            if isinstance(close_val, pd.Series):
                                price = float(close_val.iloc[0])
                            else:
                                price = float(close_val)
                            price_map[sym] = price
                except Exception as e:
                    logger.debug(f"Failed to extract batch price for {sym}: {e}")

    except Exception as e:
        logger.warning(f"Batch price fetch failed: {e}")
        # Fallback to individual fetch if batch explodes (unlikely but safe)
        pass

    # Fallback for missing symbols (e.g. if batch failed for specific ones or delisted)
    # We only try individual fetch for symbols NOT found in batch
    missing = [s for s in unique_symbols if s not in price_map]

    # Limit fallback attempts to avoid timeout if there are many missing
    # e.g. max 5 individual retries
    if missing:
        for sym in missing[:5]:
            try:
                t = yf.Ticker(sym)
                # Try fast_info
                if hasattr(t, "fast_info"):
                    val = t.fast_info.get("last_price")
                    if val is not None and not pd.isna(val):
                        price_map[sym] = float(val)
                        continue

                # Try history as last resort
                hist = t.history(period="1d")
                if not hist.empty:
                    price_map[sym] = float(hist["Close"].iloc[-1])
            except Exception as e:
                logger.debug(f"Fallback price fetch failed for {sym}: {e}")

    return price_map
