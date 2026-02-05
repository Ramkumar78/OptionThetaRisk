import pandas as pd
from typing import List, Dict, Any, Optional

def serialize_ohlc_data(df: pd.DataFrame, ticker: str) -> List[Dict[str, Any]]:
    """
    Serializes OHLCV DataFrame to a list of dictionaries suitable for Lightweight Charts.

    Args:
        df: The DataFrame containing OHLCV data.
        ticker: The ticker symbol to extract data for (if MultiIndex).

    Returns:
        A list of dictionaries with keys: time, open, high, low, close, volume.

    Raises:
        ValueError: If ticker data is not found in MultiIndex DataFrame.
    """
    if df.empty:
        return []

    # Handle MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.levels[0]:
            df = df[ticker]
        else:
            # Try uppercase
            ticker_upper = ticker.upper()
            if ticker_upper in df.columns.levels[0]:
                df = df[ticker_upper]
            else:
                raise ValueError(f"Ticker {ticker} not found in data structure")

    # Clean NaN
    df = df.dropna()

    chart_data = []

    # Helper to get value case-insensitively
    def get_val(r, key):
        val = None
        if key in r: val = r[key]
        elif key.lower() in r: val = r[key.lower()]
        elif key.capitalize() in r: val = r[key.capitalize()]

        # Convert numpy types to native python types
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                return val
        return None

    for index, row in df.iterrows():
        entry = {
            "time": index.strftime('%Y-%m-%d'),
            "open": get_val(row, 'Open'),
            "high": get_val(row, 'High'),
            "low": get_val(row, 'Low'),
            "close": get_val(row, 'Close'),
            "volume": get_val(row, 'Volume')
        }

        # Filter incomplete rows
        if all(v is not None for v in [entry['open'], entry['high'], entry['low'], entry['close']]):
            chart_data.append(entry)

    return chart_data
