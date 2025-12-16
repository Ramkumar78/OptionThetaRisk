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
        # 1. S&P 500 (US)
        tickers_sp500 = get_sp500_tickers()
        logger.info(f"Refreshing S&P 500 ({len(tickers_sp500)} tickers)...")
        get_cached_market_data(tickers_sp500, period="2y", cache_name="market_scan_v1", force_refresh=True)

        # 2. UK 350 (LSE)
        from option_auditor.uk_stock_data import get_uk_tickers
        tickers_uk = get_uk_tickers()
        logger.info(f"Refreshing UK 350 ({len(tickers_uk)} tickers)...")
        get_cached_market_data(tickers_uk, period="2y", cache_name="market_scan_uk", force_refresh=True)

        # 3. UK/Euro (Diversified/Legacy)
        from option_auditor.screener import get_uk_euro_tickers
        tickers_euro = get_uk_euro_tickers()
        logger.info(f"Refreshing UK/Euro ({len(tickers_euro)} tickers)...")
        get_cached_market_data(tickers_euro, period="2y", cache_name="market_scan_europe", force_refresh=True)

        logger.info("✅ All Caches Updated Successfully.")
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
