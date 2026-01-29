import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, ANY
import time
import os
from option_auditor.common.data_utils import fetch_batch_data_safe
from option_auditor.screener import screen_trend_followers_isa
from option_auditor.strategies.hybrid import screen_hybrid_strategy
from option_auditor.india_stock_data import get_indian_tickers_list

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
        assert mock_sleep.call_count >= 2

class TestCacheLogic:
    """Tests for the caching engine integration."""

    @patch("option_auditor.common.data_utils.fetch_batch_data_safe")
    def test_get_cached_market_data_detects_india(self, mock_fetch):
        """Verify detection of Indian tickers triggers safe mode."""
        # Use a local import to test logic in data_utils directly if needed,
        # but here we test the function itself.
        from option_auditor.common.data_utils import get_cached_market_data

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
        from option_auditor.common.data_utils import get_cached_market_data
        us_tickers = ["AAPL", "MSFT"]
        
        get_cached_market_data(us_tickers, force_refresh=True, cache_name="test_us_cache")
        
        mock_fetch.assert_called_with(
            us_tickers,
            period="2y",
            interval="1d",
            chunk_size=30,
            threads=True
        )

class TestScreenerIntegration:
    """Tests for high-level screener functions using the cache."""

    @patch("option_auditor.common.screener_utils.get_cached_market_data")
    @patch("yfinance.download")
    def test_screen_trend_followers_isa_large_list(self, mock_yf, mock_cache):
        """Verify ISA screener routes large Indian lists to cache."""
        long_list = [f"T{i}.NS" for i in range(60)]

        # Mock logic for Coverage Check:
        # First call: get_cached_market_data(None, cache_name=..., lookup_only=True)
        # Should return a DF with columns that match tickers
        cols = pd.MultiIndex.from_product([long_list, ['Close']])
        # MUST HAVE DATA to be not empty
        dummy_df = pd.DataFrame([[100.0] * len(long_list)], columns=cols)

        # Mock logic for Data Fetch:
        # Second call: get_cached_market_data(tickers, ...)

        mock_cache.side_effect = [dummy_df, dummy_df]
        
        screen_trend_followers_isa(ticker_list=long_list, region="india")
        
        # Verify calls
        calls = mock_cache.call_args_list
        # Check if any call used 'market_scan_india'
        assert any(call.kwargs.get('cache_name') == 'market_scan_india' for call in calls)

        mock_yf.assert_not_called()

    @patch("option_auditor.strategies.hybrid.get_cached_market_data")
    @patch("yfinance.download")
    def test_screen_hybrid_strategy_india(self, mock_yf, mock_cache):
        """Verify Hybrid screener routes Indian requests to correct cache name."""
        tickers = ["RELIANCE.NS", "TCS.NS"] 
        mock_cache.return_value = pd.DataFrame()
        
        # Call with region="india"
        screen_hybrid_strategy(ticker_list=tickers, region="india")
        
        # Should be called
        mock_cache.assert_called()
        args, kwargs = mock_cache.call_args
        assert kwargs.get('cache_name') == "market_scan_india"

    @patch("option_auditor.strategies.hybrid.get_cached_market_data")
    def test_screen_hybrid_strategy_defaults(self, mock_cache):
        """Verify Hybrid screener defaults for US."""
        mock_cache.return_value = pd.DataFrame()
        screen_hybrid_strategy(ticker_list=["AAPL"], region="us")
        
        # Expect watchlist_scan for small list
        mock_cache.assert_called()
        args, kwargs = mock_cache.call_args
        assert kwargs.get('cache_name') == "watchlist_scan"
