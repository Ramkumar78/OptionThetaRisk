import os
import logging
import pandas as pd
from option_auditor.common.file_utils import load_tickers_from_csv
from option_auditor.common.data_utils import fetch_exchange_rate

logger = logging.getLogger("India_Stock_Data")

# Nifty 50 & Major NSE Stocks (Yahoo Finance Tickers ending in .NS)
# Now loaded from CSV

def get_indian_tickers():
    """
    Returns the Nifty/NSE Tickers list from a CSV file.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'data', 'nifty_nse_stocks.csv')

    tickers = load_tickers_from_csv(csv_path)
    if not tickers:
        logger.warning(f"Nifty Stocks CSV not found at {csv_path}. Returning empty list.")
        return []

    return tickers

# Compatibility alias
def get_indian_tickers_list():
    return get_indian_tickers()

def apply_currency_conversion(df: pd.DataFrame, target_currency: str = 'INR') -> pd.DataFrame:
    """
    Converts DataFrame OHLCV data to the target currency.
    Assumes source data is in INR (for NSE tickers).
    """
    if df.empty or target_currency == 'INR':
        return df

    # Calculate rate once
    try:
        rate = fetch_exchange_rate("INR", target_currency)
    except Exception as e:
        logger.error(f"Failed to fetch exchange rate for conversion: {e}")
        return df

    if rate == 1.0:
        return df

    df_conv = df.copy()
    cols_to_convert = ['Open', 'High', 'Low', 'Close', 'Adj Close']

    logger.info(f"Converting India Stock Data from INR to {target_currency} (Rate: {rate})")

    for col in cols_to_convert:
        if col in df_conv.columns:
            df_conv[col] = df_conv[col] * rate

    return df_conv

# For legacy/compatibility if variables were accessed directly
INDIA_TICKERS = get_indian_tickers()
INDIAN_TICKERS_RAW = INDIA_TICKERS
