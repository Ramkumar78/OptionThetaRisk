import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy
from option_auditor.uk_stock_data import get_uk_tickers

class TestRegionStrategies:
    @pytest.fixture
    def mock_market_data(self):
        with patch('option_auditor.screener.get_cached_market_data') as mock:
            # Default to empty DF to prevent AttributeError on .columns lookup
            mock.return_value = pd.DataFrame()
            yield mock

    @pytest.fixture
    def mock_cycle(self):
        with patch('option_auditor.screener._calculate_dominant_cycle') as mock:
            mock.return_value = (20, -0.8) # Cycle bottom
            yield mock

    def test_region_uk_350_selection(self, mock_market_data, mock_cycle):
        """
        Test that region='uk' triggers the UK 350 list and 'market_scan_uk' cache.
        """
        # Execute
        screen_hybrid_strategy(region="uk", time_frame="1d")
        
        # Verify
        mock_market_data.assert_called()
        call_kwargs = mock_market_data.call_args.kwargs
        call_args = mock_market_data.call_args.args
        
        # Check Cache Key
        assert call_kwargs.get('cache_name') == 'market_scan_uk', "UK region must use 'market_scan_uk' cache"
        
        # Check Tickers
        passed_tickers = call_args[0] if call_args else call_kwargs.get('tickers')
        assert len(passed_tickers) >= 150
        assert passed_tickers == get_uk_tickers()
        assert "SHEL.L" in passed_tickers

    def test_region_uk_euro_diversified(self, mock_market_data, mock_cycle):
        """
        Test that region='uk_euro' triggers the legacy manual list and 'market_scan_europe' cache.
        """
        # Execute
        screen_hybrid_strategy(region="uk_euro", time_frame="1d")
        
        # Verify
        mock_market_data.assert_called()
        call_kwargs = mock_market_data.call_args.kwargs
        call_args = mock_market_data.call_args.args
        
        # Check Cache Key
        assert call_kwargs.get('cache_name') == 'market_scan_europe', "UK/Euro region must use 'market_scan_europe' cache"
        
        # Check Tickers
        passed_tickers = call_args[0] if call_args else call_kwargs.get('tickers')
        # Expecting the manual list (~150)
        assert len(passed_tickers) <= 200 
        assert "ASML.AS" in passed_tickers
        assert "SHEL.L" in passed_tickers

    def test_region_india_logic(self, mock_market_data, mock_cycle):
        """
        Test that region='india' triggers 'market_scan_india' cache.
        """
        # Execute
        with patch('option_auditor.screener.get_indian_tickers', return_value=["RELIANCE.NS"]):
            screen_hybrid_strategy(region="india", time_frame="1d")
        
        # Verify
        call_kwargs = mock_market_data.call_args.kwargs
        assert call_kwargs.get('cache_name') == 'market_scan_india'

    def test_region_us_default(self, mock_market_data, mock_cycle):
        """
        Test that default (US) behavior uses standard/watchlist logic.
        """
        # Execute
        screen_hybrid_strategy(region="us", time_frame="1d")
        
        # Verify
        call_kwargs = mock_market_data.call_args.kwargs
        cache_name = call_kwargs.get('cache_name')
        # Expect either watchlist_scan or market_scan_v1 depending on list size default
        assert cache_name in ["watchlist_scan", "market_scan_v1"]

