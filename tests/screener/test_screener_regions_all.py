
import pytest
from unittest.mock import patch, MagicMock
from option_auditor import screener
from option_auditor.common.screener_utils import resolve_region_tickers

@pytest.fixture
def mock_region_helper():
    # This mock works for strategies that delegate to run_screening_strategy
    # because run_screening_strategy calls resolve_region_tickers in the same module.
    with patch('option_auditor.common.screener_utils.resolve_region_tickers') as mock:
        mock.return_value = ["MOCK_TICKER"]
        yield mock

@pytest.fixture
def mock_fetch_utils():
    # Mock both direct yf and batch utils to prevent network calls
    with patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_batch, \
         patch('option_auditor.common.screener_utils.prepare_data_for_ticker') as mock_prep, \
         patch('option_auditor.common.screener_utils.yf.download') as mock_download:
        
        # Setup returns to avoid iteration errors
        mock_batch.return_value = MagicMock()
        mock_prep.return_value = None # Return None to skip processing loop body
        yield mock_download

def test_resolve_region_tickers_logic():
    """Test the helper function itself logic."""
    # Patch where they are imported in common/screener_utils.py
    with patch('option_auditor.common.screener_utils.get_uk_euro_tickers', return_value=["UK_EURO"]), \
         patch('option_auditor.common.screener_utils.get_uk_tickers', return_value=["UK_ONLY"], create=True), \
         patch('option_auditor.common.screener_utils.get_indian_tickers', return_value=["INDIA"]), \
         patch('option_auditor.common.screener_utils._get_filtered_sp500', return_value=["SP500"]), \
         patch('option_auditor.common.screener_utils.SECTOR_COMPONENTS', {"WATCH": ["WATCH_ITEM"], "TECH": ["US_TECH"]}):
        
        # UK Euro
        assert resolve_region_tickers("uk_euro") == ["UK_EURO"]
        
        # India
        assert resolve_region_tickers("india") == ["INDIA"]
        
        # SP500
        res_sp500 = resolve_region_tickers("sp500")
        assert "SP500" in res_sp500
        assert "WATCH_ITEM" in res_sp500
        
        # US/Default
        res_us = resolve_region_tickers("us")
        assert "US_TECH" in res_us

def test_screeners_use_region_helper(mock_region_helper, mock_fetch_utils):
    """Verify all updated screeners call the helper when ticker_list is None."""
    
    # 1. Turtle (Uses run_screening_strategy -> OK)
    screener.screen_turtle_setups(region="test_region")
    mock_region_helper.assert_called_with("test_region")
    
    # 2. 5/13 (Uses run_screening_strategy -> OK)
    screener.screen_5_13_setups(region="test_region_2")
    mock_region_helper.assert_called_with("test_region_2")
    
    # 3. Darvas (Uses run_screening_strategy -> OK)
    screener.screen_darvas_box(region="test_region_3")
    mock_region_helper.assert_called_with("test_region_3")

    # 4. MMS OTE (Uses run_screening_strategy -> OK)
    screener.screen_mms_ote_setups(region="test_region_4")
    mock_region_helper.assert_called_with("test_region_4")

    # 5. Bull Put (Direct Call -> NEEDS SPECIFIC PATCH)
    with patch('option_auditor.strategies.bull_put.resolve_region_tickers') as mock_bull_put_region:
        mock_bull_put_region.return_value = ["MOCK"]
        screener.screen_bull_put_spreads(region="test_region_5")
        mock_bull_put_region.assert_called_with("test_region_5")
    
    # 6. Fourier (Uses run_screening_strategy -> OK)
    screener.screen_fourier_cycles(region="test_region_6")
    mock_region_helper.assert_called_with("test_region_6")

    # 7. Hybrid (Direct Call -> NEEDS SPECIFIC PATCH)
    with patch('option_auditor.strategies.hybrid.get_cached_market_data'), \
         patch('option_auditor.strategies.hybrid.resolve_region_tickers') as mock_hybrid_region:
        mock_hybrid_region.return_value = ["MOCK"]
        screener.screen_hybrid_strategy(region="test_region_7")
        mock_hybrid_region.assert_called_with("test_region_7")

def test_screen_market_region_integration():
    """Test screen_market specifically calls helper for non-us regions."""
    # screen_market calls resolve_region_tickers directly, so we must patch it in strategies.market
    with patch('option_auditor.strategies.market.resolve_region_tickers') as mock_helper, \
         patch('option_auditor.strategies.market.screen_tickers_helper'):
         
        # Non-US
        screener.screen_market(region="india")
        mock_helper.assert_called_with("india")
        
        # SP500
        screener.screen_market(region="sp500")
        mock_helper.assert_called_with("sp500")
        
        # US
        mock_helper.reset_mock()
        screener.screen_market(region="us")
        mock_helper.assert_called_with("us")
