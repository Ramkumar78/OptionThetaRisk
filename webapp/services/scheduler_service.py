import time
import threading
import logging
import schedule
from flask import current_app
from option_auditor.strategies.master import screen_master_convergence
from webapp.cache import cache_screener_result

logger = logging.getLogger(__name__)

def run_master_scan():
    """
    Runs the Master Convergence Scan for US market and caches the result.
    This allows the /screen/master endpoint to serve instant results.
    """
    logger.info("🔄 [HEADLESS] Starting Master Convergence Scan (US)...")
    try:
        # Run US Scan (Standard 1d)
        results = screen_master_convergence(region="us", time_frame="1d")

        # Cache with key matching the route
        cache_key = ("master", "us", "1d")
        cache_screener_result(cache_key, results)

        count = len(results) if results else 0
        logger.info(f"✅ [HEADLESS] Master Scan Complete. Cached {count} items.")

    except Exception as e:
        logger.error(f"❌ [HEADLESS] Scan Failed: {e}")

def start_scheduler(app):
    """
    Starts the background scheduler in a daemon thread.
    """
    # Run once immediately on startup (in a separate thread to not block boot)
    def initial_run():
        time.sleep(10) # Wait for app to fully settle
        with app.app_context():
            run_master_scan()

    threading.Thread(target=initial_run, daemon=True).start()

    # Wrapper to inject app context into scheduled jobs
    def run_with_context():
        with app.app_context():
            run_master_scan()

    # Schedule periodic runs
    schedule.every(15).minutes.do(run_with_context)

    def run_loop():
        logger.info("🚀 [HEADLESS] Background Scheduler Loop Started.")
        while True:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"Scheduler Loop Error: {e}")
            time.sleep(1)

    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
