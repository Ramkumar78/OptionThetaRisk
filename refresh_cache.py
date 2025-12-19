import time
import schedule
import logging
from option_auditor.sp500_data import get_sp500_tickers
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.constants import LIQUID_OPTION_TICKERS, SECTOR_COMPONENTS

logging.basicConfig(level=logging.INFO)

def refresh_job():
    print(f"🔄 [BACKGROUND] Starting Cache Refresh at {time.ctime()}")

    # 1. Refresh S&P 500
    sp500 = get_sp500_tickers()
    get_cached_market_data(sp500, period="2y", cache_name="market_scan_v1", force_refresh=True)

    # 2. Refresh Liquid Options (Used by Fortress Strategy)
    get_cached_market_data(LIQUID_OPTION_TICKERS, period="1y", cache_name="market_scan_us_liquid", force_refresh=True)

    # 3. Refresh Sectors
    sector_tickers = []
    for t_list in SECTOR_COMPONENTS.values():
        if isinstance(t_list, list): sector_tickers.extend(t_list)
    sector_tickers = list(set(sector_tickers))
    get_cached_market_data(sector_tickers, period="2y", cache_name="market_scan_us_sectors", force_refresh=True)

    # 4. Refresh UK/Euro (Optional but good to have if used)
    # Keeping minimal set as per user instruction to "Fix" the placebo.
    # The user provided a specific block for refresh_cache.py in the prompt. I will stick to that.

    print(f"✅ [BACKGROUND] Cache Refresh Complete at {time.ctime()}")

# Run immediately on startup
try:
    refresh_job()
except Exception as e:
    print(f"Startup refresh failed: {e}")

# Schedule every 4 hours
schedule.every(4).hours.do(refresh_job)

while True:
    schedule.run_pending()
    time.sleep(60)
