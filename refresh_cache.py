import time
import schedule
import logging
from option_auditor.sp500_data import get_sp500_tickers
from option_auditor.common.data_utils import get_cached_market_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def job():
    logger.info("🔄 Background Job: Refreshing S&P 500 Cache...")
    try:
        tickers = get_sp500_tickers()
        # Also include WATCH list logic if needed, but the primary big data is SP500.
        # The prompt says: "Run this script automatically every 4 hours...".
        # It calls get_cached_market_data with cache_name="market_scan_v1".
        # We need to make sure we use the same cache_name as in screener.py (sp500 -> market_scan_v1).

        # The screener logic uses "market_scan_v1" for list > 100.
        # Since sp500 is > 100, we use "market_scan_v1".

        # Force refresh logic:
        # We set force_refresh=True to ensure we download fresh data regardless of cache age.
        get_cached_market_data(tickers, period="2y", cache_name="market_scan_v1", force_refresh=True)
        logger.info("✅ Cache Updated.")
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")

if __name__ == "__main__":
    # Run immediately on startup
    job()

    # Schedule every 4 hours
    schedule.every(4).hours.do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)
