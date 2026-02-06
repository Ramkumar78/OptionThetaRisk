import pandas as pd
import numpy as np
import logging
import yfinance as yf
from option_auditor.common.screener_utils import fetch_batch_data_safe, resolve_ticker

logger = logging.getLogger(__name__)

def calculate_correlation_matrix(ticker_list: list = None, period: str = "1y", interval: str = "1d") -> dict:
    """
    Calculates the correlation matrix of daily returns for the given tickers.

    Returns:
        dict: {
            "tickers": [list of tickers],
            "matrix": [[val, val], ...], # 2D array
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
        }
    """
    if not ticker_list:
        return {"error": "No tickers provided"}

    # Resolve aliases
    clean_tickers = [resolve_ticker(t) for t in ticker_list]
    # Remove duplicates
    clean_tickers = sorted(list(set(clean_tickers)))

    if len(clean_tickers) < 2:
        return {"error": "Need at least 2 tickers for correlation."}

    try:
        # Fetch data
        data = fetch_batch_data_safe(clean_tickers, period=period, interval=interval)

        if data.empty:
            return {"error": "No data fetched."}

        prices_dict = {}

        if isinstance(data.columns, pd.MultiIndex):
            # Assumes group_by='ticker' -> Level 0 is Ticker
            for t in clean_tickers:
                try:
                    # Check if ticker exists in Level 0
                    if t in data.columns.levels[0]:
                        ticker_df = data[t]
                        if 'Adj Close' in ticker_df.columns:
                            prices_dict[t] = ticker_df['Adj Close']
                        elif 'Close' in ticker_df.columns:
                            prices_dict[t] = ticker_df['Close']
                except Exception:
                    continue
        else:
            # Single ticker or flat structure (unlikely with fetch_batch_data_safe > 1 ticker)
            # If flat, verify columns
            # But we enforced clean_tickers > 2
            pass

        if not prices_dict:
             return {"error": "Could not extract prices from data."}

        prices = pd.DataFrame(prices_dict)

        # Drop columns with all NaNs
        prices = prices.dropna(axis=1, how='all')

        # Drop rows with any NaNs to ensure matching periods
        # Alternatively, pairwise correlation handles NaNs, but for a matrix we usually want a common period.
        # Let's drop rows where any ticker is missing to be strict about the window.
        prices = prices.dropna(how='any')

        if len(prices) < 20:
             return {"error": "Insufficient overlapping history (min 20 days)."}

        # Calculate Returns
        returns = prices.pct_change().dropna()

        # Correlation
        corr_matrix = returns.corr()

        # Format for JSON
        # replace NaN with None for JSON compliance
        matrix_values = corr_matrix.where(pd.notnull(corr_matrix), None).values.tolist()
        columns = corr_matrix.columns.tolist()

        return {
            "tickers": columns,
            "matrix": matrix_values,
            "start_date": returns.index[0].strftime('%Y-%m-%d'),
            "end_date": returns.index[-1].strftime('%Y-%m-%d')
        }

    except Exception as e:
        logger.exception(f"Correlation calc failed: {e}")
        return {"error": str(e)}

def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr

def get_market_regime(sp500_data: pd.DataFrame) -> dict:
    """
    Determines market regime based on SP500 data and VIX.

    Returns:
        dict: {
            "regime": str,         # e.g., 'Stormy (High Risk)', 'Bullish (Safe)'
            "market_climate": str, # e.g., 'Quiet', 'Turbulent', 'Panic'
            "vix": float or None   # e.g., 18.5
        }
    """
    result = {
        "regime": "Unknown (No Data)",
        "market_climate": "Unknown",
        "vix": None
    }

    # --- 1. Fetch VIX for Market Climate ---
    try:
        vix_df = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
        if not vix_df.empty:
             # Handle MultiIndex if present
            if isinstance(vix_df.columns, pd.MultiIndex):
                # Try to find Close col
                try:
                    # If columns are (Price, Ticker) or (Ticker, Price)
                    # auto_adjust=True returns 'Close' usually.
                    # Flatten or select
                    vix_series = vix_df['Close']
                    if isinstance(vix_series, pd.DataFrame):
                        vix_series = vix_series.iloc[:, 0] # Take first col if multiple (should be one ticker)
                except Exception:
                     vix_series = vix_df.iloc[:, 0] # Fallback
            else:
                 vix_series = vix_df['Close']

            current_vix = float(vix_series.iloc[-1])
            result["vix"] = current_vix

            if current_vix < 15:
                result["market_climate"] = "Quiet"
            elif 15 <= current_vix < 25:
                result["market_climate"] = "Turbulent"
            else:
                result["market_climate"] = "Panic"
        else:
             logger.warning("VIX data empty.")
    except Exception as e:
        logger.warning(f"Failed to fetch VIX: {e}")


    # --- 2. Determine Regime from SP500 Data ---
    if sp500_data is None or sp500_data.empty:
        return result

    df = sp500_data.copy()

    # Handle MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        try:
            # Flatten to single level if possible, assuming one ticker
            # Or just take the last level
            df.columns = df.columns.get_level_values(-1)
        except Exception:
            pass

    required_cols = ['High', 'Low', 'Close']
    if not all(col in df.columns for col in required_cols):
         result["regime"] = "Unknown (Missing Columns)"
         return result

    # Ensure enough data
    if len(df) < 200:
        result["regime"] = "Unknown (Insufficient History)"
        return result

    try:
        # Calculate Indicators
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['RSI'] = _calculate_rsi(df['Close'])
        df['ATR'] = _calculate_atr(df)

        # Get last values
        last_row = df.iloc[-1]

        if pd.isna(last_row['SMA200']) or pd.isna(last_row['RSI']) or pd.isna(last_row['ATR']):
            result["regime"] = "Unknown (NaN Indicators)"
            return result

        current_atr = last_row['ATR']
        current_close = last_row['Close']
        current_sma = last_row['SMA200']
        current_rsi = last_row['RSI']

        # ATR Percentile Logic
        atr_history = df['ATR'].dropna()
        # Percentile rank of current_atr within atr_history
        # Using strict inequality to match "top 90th"
        percentile = (atr_history < current_atr).mean() * 100

        # Logic
        if percentile >= 90:
            result["regime"] = "Stormy (High Risk)"
        elif current_close < current_sma:
            result["regime"] = "Bearish (Caution)"
        elif current_close > current_sma and current_rsi > 50:
            result["regime"] = "Bullish (Safe)"
        else:
            result["regime"] = "Neutral (Sideways)"

    except Exception as e:
        logger.error(f"Error determining market regime: {e}")
        result["regime"] = "Unknown (Error)"

    return result
