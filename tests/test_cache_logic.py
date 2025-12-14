import os
import shutil
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import get_cached_market_data, CACHE_DIR

@pytest.fixture
def clean_cache():
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    yield
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)

def test_get_cached_market_data_creates_cache(clean_cache):
    tickers = ["AAPL", "MSFT"]

    # Mock fetch_batch_data_safe to return dummy data
    with patch("option_auditor.common.data_utils.fetch_batch_data_safe") as mock_fetch:
        # Create a dummy dataframe
        df = pd.DataFrame({
            "Close": [100.0, 101.0],
            "Volume": [1000, 2000]
        }, index=pd.to_datetime(["2023-01-01", "2023-01-02"]))
        # Make it look like a multi-index result if needed, or just flat
        # get_cached_market_data just returns what fetch returns.
        mock_fetch.return_value = df

        # 1. First Call: Should fetch and save
        result1 = get_cached_market_data(tickers, cache_name="test_cache")

        assert not result1.empty
        assert mock_fetch.call_count == 1
        assert os.path.exists(os.path.join(CACHE_DIR, "test_cache.parquet"))

        # 2. Second Call: Should load from cache (fetch not called again)
        result2 = get_cached_market_data(tickers, cache_name="test_cache")

        assert not result2.empty
        assert mock_fetch.call_count == 1 # Still 1
        pd.testing.assert_frame_equal(result1, result2)

def test_screener_uses_cache():
    from option_auditor.screener import screen_master_convergence

    # Mock get_cached_market_data
    with patch("option_auditor.screener.get_cached_market_data") as mock_cache:
        mock_cache.return_value = pd.DataFrame() # Return empty to avoid downstream processing errors

        # Call with list > 100
        long_list = ["TICKER"] * 101
        screen_master_convergence(ticker_list=long_list)

        # Verify it called with cache_name="market_scan_v1"
        mock_cache.assert_called_with(long_list, period="2y", cache_name="market_scan_v1")

        # Call with list <= 100
        short_list = ["AAPL"]
        screen_master_convergence(ticker_list=short_list)

        # Verify it called with cache_name="watchlist_scan"
        mock_cache.assert_called_with(short_list, period="2y", cache_name="watchlist_scan")
