import logging
import os
import csv
from option_auditor.common.constants import SECTOR_COMPONENTS

logger = logging.getLogger("SP500_Data")

def get_sp500_tickers():
    """
    Returns the S&P 500 list from a CSV file.
    Falls back to hardcoded list if CSV is missing.
    """
    tickers = []

    # Path to CSV file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'data', 'sp500_tickers.csv')

    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        tickers.append(row[0].strip().upper())

            # Remove duplicates and sort
            unique_tickers = sorted(list(set(tickers)))
            logger.info(f"Loaded {len(unique_tickers)} tickers from CSV: {csv_path}")
            return unique_tickers
        except Exception as e:
            logger.error(f"Error loading S&P 500 from CSV: {e}")
    else:
        logger.warning(f"S&P 500 CSV not found at {csv_path}. Falling back to hardcoded components.")

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
# We don't have names in the CSV, so we leave this empty or load if available
SP500_NAMES = {}
