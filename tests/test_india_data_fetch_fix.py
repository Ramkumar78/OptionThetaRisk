import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, ANY
import time
from option_auditor.common.data_utils import fetch_batch_data_safe, get_cached_market_data
from option_auditor.screener import screen_trend_followers_isa

# Mock Data
def create_mock_df(tickers):
    # minimal DF
    data = {}
    for t in tickers:
        data[(t, "Close")] = [100.0] * 2
    
    # create multiindex columns
    cols = pd.MultiIndex.from_tuples([(t, "Close") for t in tickers], names=["Ticker", "Price"])
    df = pd.DataFrame([[100]*len(tickers), [101]*len(tickers)], columns=cols, index=pd.to_datetime(["2023-01-01", "2023-01-02"]))
    return df

class TestIndiaDataFetchFix:
    
    @patch("option_auditor.common.data_utils.yf.download")
    def test_fetch_batch_data_safe_chunking(self, mock_download):
        """Verify fetch_batch_data_safe chunks correctly and passes threads arg."""
        tickers = [f"T{i}" for i in range(100)]
        mock_download.return_value = pd.DataFrame() # Return empty to keep it simple, checking logic mostly
        
        # Call with chunk_size=30
        fetch_batch_data_safe(tickers, chunk_size=30, threads=True)
        
        # 100 / 30 = 4 chunks (30, 30, 30, 10)
        assert mock_download.call_count == 4
        
        # Verify call args for one of them
        # call_args_list[0] -> (args, kwargs)
        args, kwargs = mock_download.call_args_list[0]
        assert kwargs['threads'] is True
        assert kwargs['group_by'] == 'ticker'
        
    @patch("option_auditor.common.data_utils.yf.download")
    @patch("option_auditor.common.data_utils.time.sleep")
    def test_fetch_batch_data_safe_sleeps(self, mock_sleep, mock_download):
        """Verify sleep is called between chunks."""
        tickers = [f"T{i}" for i in range(100)]
        mock_download.return_value = pd.DataFrame()
        
        fetch_batch_data_safe(tickers, chunk_size=30)
        
        # Should sleep 3 times (between 4 chunks)
        # However, logic is if i > 0: sleep. So for 0 it doesn't, for 1, 2, 3 it does.
        # Total calls >= 3
        assert mock_sleep.call_count >= 3

    @patch("option_auditor.common.data_utils.fetch_batch_data_safe")
    def test_get_cached_market_data_detects_india(self, mock_fetch):
        """Verify get_cached_market_data detects Indian tickers and uses safe settings."""
        # 1. Indian Tickers
        indian_tickers = ["RELIANCE.NS", "TCS.NS"]
        # Force refresh to trigger download logic
        get_cached_market_data(indian_tickers, force_refresh=True, cache_name="test_india")
        
        # Verify fetch_batch_data_safe called with threads=True (as per my implementation)
        mock_fetch.assert_called_with(
            indian_tickers, 
            period="2y", 
            interval="1d", 
            chunk_size=30, 
            threads=True
        )

    @patch("option_auditor.screener.get_cached_market_data")
    @patch("option_auditor.screener.yf.download")
    def test_screener_uses_cache_for_large_lists(self, mock_yf, mock_cache):
        """Verify screen_trend_followers_isa uses cache for > 50 tickers."""
        
        # 1. Large List (Mocking > 50)
        long_list = [f"T{i}" for i in range(60)]
        
        # Mock logic to return empty to stop further processing in screener
        mock_cache.return_value = pd.DataFrame()
        
        screen_trend_followers_isa(ticker_list=long_list, region="india")
        
        # Should call get_cached_market_data with specific key
        mock_cache.assert_called_once_with(long_list, period="2y", cache_name="market_scan_india")
        
        # Should NOT call yf.download directly
        mock_yf.assert_not_called()
        
    @patch("option_auditor.screener.get_cached_market_data")
    @patch("option_auditor.screener.yf.download")
    def test_screener_uses_direct_download_for_small_lists(self, mock_yf, mock_cache):
        """Verify screen_trend_followers_isa uses direct download for small lists."""
        
        # 1. Small List
        short_list = ["RELIANCE.NS"]
        
        mock_yf.return_value = pd.DataFrame()
        
        screen_trend_followers_isa(ticker_list=short_list, region="india")
        
        # Should call yf.download
        mock_yf.assert_called_once()
        
        # Should NOT call get_cached_market_data
        mock_cache.assert_not_called()
