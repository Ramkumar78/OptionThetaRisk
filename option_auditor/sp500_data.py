import logging
from option_auditor.common.constants import SECTOR_COMPONENTS

logger = logging.getLogger("SP500_Data")

def get_sp500_tickers():
    """
    Returns the S&P 500 list by aggregating hardcoded sector components
    from option_auditor.common.constants.

    This is faster and more reliable than scraping Wikipedia.
    """
    tickers = []
    try:
        # Iterate through all sectors (Technology, Financials, etc.)
        for sector, component_list in SECTOR_COMPONENTS.items():
            # We exclude the generic 'WATCH' list to keep this a pure S&P 500 proxy
            # unless you specifically want your watchlist included.
            if sector != "WATCH":
                tickers.extend(component_list)

        # Remove duplicates and sort
        unique_tickers = sorted(list(set(tickers)))

        logger.info(f"Loaded {len(unique_tickers)} tickers from local SECTOR_COMPONENTS.")
        return unique_tickers

    except Exception as e:
        logger.error(f"Error loading S&P 500 from constants: {e}")
        # Fallback to a small liquid list if constants file is broken
        return ["SPY", "QQQ", "IWM", "NVDA", "MSFT", "AAPL"]

SP500_TICKERS = get_sp500_tickers()
