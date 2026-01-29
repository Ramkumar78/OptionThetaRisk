import os
import shutil
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import get_cached_market_data, CACHE_DIR

@pytest.fixture
def mock_cache_dir(tmp_path):
    # Patch the CACHE_DIR in the module to point to a temporary directory
    d = tmp_path / "cache_test"
    d.mkdir()
    
    with patch("option_auditor.common.data_utils.CACHE_DIR", str(d)):
        yield str(d)

def test_get_cached_market_data_creates_cache(mock_cache_dir):
    tickers = ["AAPL", "MSFT"]
    cache_path = os.path.join(mock_cache_dir, "test_cache.parquet")

    # Mock fetch_batch_data_safe to return dummy data
    with patch("option_auditor.common.data_utils.fetch_batch_data_safe") as mock_fetch:
        # Create a dummy dataframe
        df = pd.DataFrame({
            "Close": [100.0, 101.0],
            "Volume": [1000, 2000]
        }, index=pd.to_datetime(["2023-01-01", "2023-01-02"]))
        mock_fetch.return_value = df

        # 1. First Call: Should fetch and save
        result1 = get_cached_market_data(tickers, cache_name="test_cache")

        assert not result1.empty
        assert mock_fetch.call_count == 1
        assert os.path.exists(cache_path)

        # 2. Second Call: Should load from cache (fetch not called again)
        result2 = get_cached_market_data(tickers, cache_name="test_cache")

        assert not result2.empty
        assert mock_fetch.call_count == 1 # Still 1
        pd.testing.assert_frame_equal(result1, result2)

def test_screener_uses_cache():
    from option_auditor.screener import screen_master_convergence

    # Mock get_cached_market_data
    with patch("option_auditor.common.screener_utils.get_cached_market_data") as mock_cache:
        # We need it to return something when lookup_only=True (first call for > 50 tickers)
        # and something (or empty) for subsequent calls.

        # side_effect allows different returns for different calls
        def side_effect(*args, **kwargs):
            if kwargs.get('lookup_only'):
                 # Simulate cache hit for coverage check
                 # Need a DF with MultiIndex columns to satisfy coverage check logic
                 # Must match the tickers in long_list for coverage > 0.6
                 tickers = [f"T{i}" for i in range(101)]
                 iterables = [tickers, ['Close']]
                 cols = pd.MultiIndex.from_product(iterables)
                 return pd.DataFrame(columns=cols)
            return pd.DataFrame()

        mock_cache.side_effect = side_effect

        # Call with list > 100
        long_list = [f"T{i}" for i in range(101)]
        screen_master_convergence(ticker_list=long_list)

        # Verify it called with cache_name="market_scan_v1"
        # We search through call_args_list to find the main fetch call
        # Or even the lookup call is fine to verify correct routing
        found_any_v1 = False
        for call in mock_cache.call_args_list:
            args, kwargs = call
            if kwargs.get('cache_name') == 'market_scan_v1':
                found_any_v1 = True
                break

        assert found_any_v1, "Did not find any call for market_scan_v1"

        # Call with list <= 100
        short_list = ["AAPL"]
        screen_master_convergence(ticker_list=short_list)

        # Verify it called with cache_name="watchlist_scan"
        found_watch = False
        for call in mock_cache.call_args_list:
            args, kwargs = call
            if kwargs.get('cache_name') == 'watchlist_scan':
                found_watch = True
                break

        assert found_watch, "Did not find expected fetch call for watchlist_scan"
