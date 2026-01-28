
import pytest
import time
from unittest.mock import patch, MagicMock
from option_auditor import screener
from option_auditor.common.constants import LIQUID_OPTION_TICKERS
import pandas as pd
import numpy as np

@patch('option_auditor.common.screener_utils.get_cached_market_data')
@patch('yfinance.download')
def test_screen_fortress_performance(mock_download, mock_get_cached_data):
    """
    Test the performance of the Fortress screener using mocks to ensure speed and stability.
    """
    # Mock VIX download
    mock_download.return_value = pd.DataFrame({'Close': [15.0]}, index=[pd.Timestamp.now()])

    # Mock cached market data return
    # Create a DataFrame that mimics the structure of `market_scan_us_liquid`
    # We need to ensure it's performant to generate this mock data
    tickers = LIQUID_OPTION_TICKERS[:10] # Test with a subset to be fast, or full set if we want to test logic speed
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200)

    # Create a MultiIndex DataFrame
    # Using numpy for speed
    data = np.random.randn(200, len(tickers) * 5)
    cols = pd.MultiIndex.from_product([tickers, ['Open', 'High', 'Low', 'Close', 'Volume']])
    df = pd.DataFrame(data, index=dates, columns=cols)
    
    # Ensure reasonable values
    df.loc[:, (slice(None), 'Close')] = 100.0
    df.loc[:, (slice(None), 'High')] = 105.0
    df.loc[:, (slice(None), 'Low')] = 95.0
    df.loc[:, (slice(None), 'Open')] = 100.0
    df.loc[:, (slice(None), 'Volume')] = 1000000

    mock_get_cached_data.return_value = df

    print(f"\nScanning {len(tickers)} tickers for Fortress (Mocked)...")

    start_time = time.time()
    results = screener.screen_dynamic_volatility_fortress(ticker_list=tickers)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\nFortress Scan took {duration:.2f} seconds")
    print(f"Results found: {len(results)}")
    
    if results:
        print(f"Sample Result: {results[0]}")
        
    # Assert extremely fast execution with mocks
    assert duration < 5.0, f"Scan took too long: {duration:.2f}s"
    assert isinstance(results, list)
