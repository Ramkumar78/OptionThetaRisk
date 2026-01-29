import logging
from option_auditor.common.data_loader import load_tickers_from_csv

logger = logging.getLogger("India_Stock_Data")

# Nifty 50 & Major NSE Stocks (Yahoo Finance Tickers ending in .NS)
# Now loaded from CSV

def get_indian_tickers():
    """
    Returns the Nifty/NSE Tickers list from a CSV file.
    """
    return load_tickers_from_csv('nifty_nse_stocks.csv', column_name='Ticker')

# Compatibility alias
def get_indian_tickers_list():
    return get_indian_tickers()

# For legacy/compatibility if variables were accessed directly
# Note: This will now execute at import time, which is consistent with previous behavior
INDIA_TICKERS = get_indian_tickers()
INDIAN_TICKERS_RAW = INDIA_TICKERS
