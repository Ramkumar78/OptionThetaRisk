import os
import logging
from option_auditor.common.file_utils import load_tickers_from_csv

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

# For legacy/compatibility if variables were accessed directly
INDIA_TICKERS = get_indian_tickers()
INDIAN_TICKERS_RAW = INDIA_TICKERS
