import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, ANY
import time
import os
from option_auditor.common.data_utils import fetch_batch_data_safe, get_cached_market_data
from option_auditor.screener import screen_trend_followers_isa, screen_hybrid_strategy
from option_auditor.india_stock_data import get_indian_tickers_list, INDIAN_TICKERS_RAW

# Mock Data Helper
def create_mock_df(tickers):
    # Create a MultiIndex DataFrame to simulate yfinance group_by='ticker' output
    # Columns: (Ticker, Price)
    # Ensure we return valid data
    data = {}
    for t in tickers:
        data[(t, "Close")] = [100.0, 101.0, 102.0]
        data[(t, "High")] = [105.0, 106.0, 107.0]
        data[(t, "Low")] = [95.0, 96.0, 97.0]
        data[(t, "Open")] = [98.0, 99.0, 100.0]
        data[(t, "Volume")] = [1000000, 1000000, 1000000]

    cols = pd.MultiIndex.from_tuples(data.keys(), names=["Ticker", "Price"])
    df = pd.DataFrame(data.values(), columns=cols, index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]))
    return df

class TestIndiaTickerList:
    """Tests for the integrity of the Indian Ticker List."""

    def test_list_contains_only_nse_tickers(self):
        """Verify all tickers end with .NS suffix."""
        tickers = get_indian_tickers_list()
        invalid = [t for t in tickers if not t.endswith('.NS')]
        assert not invalid, f"Found non-NSE tickers: {invalid}"

    def test_list_limit_and_length(self):
        """Verify the list returns exactly 100 tickers."""
        tickers = get_indian_tickers_list()
        assert len(tickers) == 100, f"Expected 100 tickers, got {len(tickers)}"

    def test_list_preserves_order(self):
        """Verify the list preserves market cap order (Reliance, TCS, HDFC first)."""
        tickers = get_indian_tickers_list()
        # Top 3 based on static list we provided
        # Order is preserved from CSV which matches original list
        assert tickers[0] == "RELIANCE.NS"
        assert tickers[1] == "TCS.NS"
        assert tickers[2] == "HDFCBANK.NS"

    def test_no_duplicates(self):
        """Verify there are no duplicate tickers."""
        tickers = get_indian_tickers_list()
        assert len(tickers) == len(set(tickers))

class TestDataFetchingRobustness:
    """Tests for safe data fetching logic (chunking, sleep, retries)."""

    @patch("option_auditor.common.data_utils.yf.download")
    def test_fetch_batch_data_safe_chunking(self, mock_download):
        """Verify functionality splits requests into chunks of 30."""
        tickers = [f"T{i}" for i in range(100)]
        mock_download.return_value = pd.DataFrame()
        
        fetch_batch_data_safe(tickers, chunk_size=30, threads=True)
        
        # 100 items / 30 = 4 chunks (30, 30, 30, 10)
        assert mock_download.call_count == 4
        
        # Verify first call args
        args, kwargs = mock_download.call_args_list[0]
        assert len(args[0]) == 30
        assert kwargs['threads'] is True
        assert kwargs['group_by'] == 'ticker'

    @patch("option_auditor.common.data_utils.yf.download")
    @patch("option_auditor.common.data_utils.time.sleep")
    def test_fetch_batch_data_safe_sleeps(self, mock_sleep, mock_download):
        """Verify sleep is inserted for rate limiting between chunks."""
        tickers = [f"T{i}" for i in range(70)] # 3 chunks: 30, 30, 10
        mock_download.return_value = pd.DataFrame()
        
        fetch_batch_data_safe(tickers, chunk_size=30)
        
        # Sleep called for i=1, i=2. Total 2 sleeps.
        # Implementation: if i > 0: sleep
        assert mock_sleep.call_count >= 2

class TestCacheLogic:
    """Tests for the caching engine integration."""

    @patch("option_auditor.common.data_utils.fetch_batch_data_safe")
    def test_get_cached_market_data_detects_india(self, mock_fetch):
        """Verify detection of Indian tickers triggers safe mode."""
        indian_tickers = ["RELIANCE.NS", "SBI.NS"]
        
        # Force refresh to ignore any disk file and ensure fetch is called
        get_cached_market_data(indian_tickers, force_refresh=True, cache_name="test_india_cache")
        
        mock_fetch.assert_called_with(
            indian_tickers,
            period="2y",
            interval="1d",
            chunk_size=30, # Expect 30 for safety
            threads=True # Expect True as per implementation
        )

    @patch("option_auditor.common.data_utils.fetch_batch_data_safe")
    def test_get_cached_market_data_us_default(self, mock_fetch):
        """Verify normal behavior for US tickers."""
        us_tickers = ["AAPL", "MSFT"]
        
        get_cached_market_data(us_tickers, force_refresh=True, cache_name="test_us_cache")
        
        # When not India, it still calls fetch_batch_data_safe, 
        # but inside get_cached_market_data the loop for 'Indian tickers detected' 
        # sets variables. 
        # Actually logic is: default chunk=30 is PASSED explicitly in current implementation line 106.
        # But logging is different. Here we just ensure it calls the fetcher.
        mock_fetch.assert_called_with(
            us_tickers,
            period="2y",
            interval="1d",
            chunk_size=30,
            threads=True
        )

class TestScreenerIntegration:
    """Tests for high-level screener functions using the cache."""

    @patch("option_auditor.screener.get_cached_market_data")
    @patch("option_auditor.screener.yf.download")
    def test_screen_trend_followers_isa_large_list(self, mock_yf, mock_cache):
        """Verify ISA screener routes large Indian lists to cache."""
        # > 50 tickers
        long_list = [f"T{i}.NS" for i in range(60)]
        mock_cache.return_value = pd.DataFrame() # Stop processing
        
        screen_trend_followers_isa(ticker_list=long_list, region="india")
        
        mock_cache.assert_called_once_with(long_list, period="2y", cache_name="market_scan_india")
        mock_yf.assert_not_called()

    @patch("option_auditor.screener.get_cached_market_data")
    @patch("option_auditor.screener.yf.download")
    def test_screen_hybrid_strategy_india(self, mock_yf, mock_cache):
        """Verify Hybrid screener routes Indian requests to correct cache name."""
        tickers = ["RELIANCE.NS", "TCS.NS"] 
        mock_cache.return_value = pd.DataFrame()
        
        # Call with region="india"
        screen_hybrid_strategy(ticker_list=tickers, region="india")
        
        # Even if list is small, hybrid caching logic uses 'market_scan_india' if region="india"
        mock_cache.assert_called_once()
        args, kwargs = mock_cache.call_args
        assert kwargs['cache_name'] == "market_scan_india"

    @patch("option_auditor.screener.get_cached_market_data")
    def test_screen_hybrid_strategy_defaults(self, mock_cache):
        """Verify Hybrid screener defaults for US."""
        mock_cache.return_value = pd.DataFrame()
        screen_hybrid_strategy(ticker_list=["AAPL"], region="us")
        
        # Expect watchlist_scan for small list
        args, kwargs = mock_cache.call_args
        assert kwargs['cache_name'] == "watchlist_scan"
