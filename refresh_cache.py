import time
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CacheWorker")

# Add the current directory to sys.path to ensure modules can be imported
sys.path.append(os.getcwd())

try:
    from option_auditor.common.data_utils import get_cached_market_data
    from option_auditor.sp500_data import get_sp500_tickers
    from option_auditor.india_stock_data import get_indian_tickers
    from option_auditor.uk_stock_data import get_uk_tickers, get_uk_euro_tickers
    from option_auditor.us_stock_data import get_united_states_stocks
except ImportError as e:
    logger.critical(f"Failed to import required modules: {e}")
    sys.exit(1)

def refresh_all():
    logger.info("Starting Cache Refresh Cycle...")

    # 1. S&P 500 / US Market Scan
    try:
        logger.info("Refreshing S&P 500 cache (market_scan_v1)...")
        sp500 = get_sp500_tickers()
        if sp500:
             get_cached_market_data(sp500, period="2y", cache_name="market_scan_v1", force_refresh=True)
        else:
            logger.warning("No S&P 500 tickers found.")
    except Exception as e:
        logger.error(f"Error refreshing S&P 500: {e}")

    # 2. US Liquid / All Stocks
    try:
        logger.info("Refreshing US Liquid cache (market_scan_us_liquid)...")
        us_stocks = get_united_states_stocks()
        if us_stocks:
            get_cached_market_data(us_stocks, period="1y", cache_name="market_scan_us_liquid", force_refresh=True)
        else:
            logger.warning("No US stocks found.")
    except Exception as e:
        logger.error(f"Error refreshing US Liquid: {e}")

    # 3. India
    try:
        logger.info("Refreshing India cache (market_scan_india)...")
        india = get_indian_tickers()
        if india:
            get_cached_market_data(india, period="2y", cache_name="market_scan_india", force_refresh=True)
        else:
            logger.warning("No India tickers found.")
    except Exception as e:
        logger.error(f"Error refreshing India: {e}")

    # 4. UK
    try:
        logger.info("Refreshing UK cache (market_scan_uk)...")
        uk = get_uk_tickers()
        if uk:
             get_cached_market_data(uk, period="2y", cache_name="market_scan_uk", force_refresh=True)
        else:
            logger.warning("No UK tickers found.")
    except Exception as e:
        logger.error(f"Error refreshing UK: {e}")

    # 5. Europe
    try:
        logger.info("Refreshing Europe cache (market_scan_europe)...")
        euro = get_uk_euro_tickers()
        if euro:
             get_cached_market_data(euro, period="2y", cache_name="market_scan_europe", force_refresh=True)
        else:
            logger.warning("No Europe tickers found.")
    except Exception as e:
        logger.error(f"Error refreshing Europe: {e}")

    logger.info("Cache Refresh Cycle Completed.")

if __name__ == "__main__":
    logger.info("Cache Worker initialized.")

    while True:
        try:
            refresh_all()
        except Exception as e:
            logger.error(f"Unexpected error in refresh loop: {e}")

        # Sleep for 4 hours
        sleep_duration = 4 * 3600
        logger.info(f"Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)
