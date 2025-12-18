
import pytest
import time
from option_auditor import screener
from option_auditor.common.constants import LIQUID_OPTION_TICKERS

def test_screen_fortress_performance():
    """
    Test the performance of the Fortress screener.
    """
    print(f"\nScanning {len(LIQUID_OPTION_TICKERS)} tickers for Fortress (Cold Start)...")
    
    # Clean cache to simulate cold start
    cache_path = "e:/PycharmProjects/OptionThetaRisk/cache_data/market_scan_us_liquid.parquet"
    import os
    if os.path.exists(cache_path):
        os.remove(cache_path)
        print("Cache cleared.")

    start_time = time.time()
    results = screener.screen_dynamic_volatility_fortress()
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\nFortress Scan took {duration:.2f} seconds")
    print(f"Results found: {len(results)}")
    
    if results:
        print(f"Sample Result: {results[0]}")
        
    # Assert reasonable time (e.g. < 45 seconds for cold start)
    # If standard is 60s, we want to be safe.
    assert duration < 60, f"Scan took too long: {duration:.2f}s"
    assert isinstance(results, list)
