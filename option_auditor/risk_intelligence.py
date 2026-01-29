import pandas as pd
import numpy as np
import logging
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
