import os
import csv
import logging

logger = logging.getLogger("India_Stock_Data")

# Nifty 50 & Major NSE Stocks (Yahoo Finance Tickers ending in .NS)
# Now loaded from CSV

def get_indian_tickers():
    """
    Returns the Nifty/NSE Tickers list from a CSV file.
    """
    tickers = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'data', 'nifty_nse_stocks.csv')

    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                # Skip header if present, or just assume first col is ticker

                header_skipped = False
                for row in reader:
                    if not row: continue
                    val = row[0].strip()

                    if not header_skipped and val.lower() == "ticker":
                        header_skipped = True
                        continue

                    if val:
                        tickers.append(val.upper())

            # Use dict.fromkeys to remove duplicates while preserving order
            unique_tickers = list(dict.fromkeys(tickers))
            # logger.info(f"Loaded {len(unique_tickers)} tickers from CSV: {csv_path}")
            return unique_tickers
        except Exception as e:
            logger.error(f"Error loading Nifty Stocks from CSV: {e}")
            return []
    else:
        logger.warning(f"Nifty Stocks CSV not found at {csv_path}. Returning empty list.")
        return []

# Compatibility alias
def get_indian_tickers_list():
    return get_indian_tickers()

# For legacy/compatibility if variables were accessed directly
INDIA_TICKERS = get_indian_tickers()
INDIAN_TICKERS_RAW = INDIA_TICKERS
