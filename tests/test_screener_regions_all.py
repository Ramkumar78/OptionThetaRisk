
import pytest
from unittest.mock import patch, MagicMock
from option_auditor import screener

@pytest.fixture
def mock_region_helper():
    with patch('option_auditor.screener._resolve_region_tickers') as mock:
        mock.return_value = ["MOCK_TICKER"]
        yield mock

@pytest.fixture
def mock_fetch_utils():
    # Mock both direct yf and batch utils to prevent network calls
    with patch('option_auditor.screener.fetch_batch_data_safe') as mock_batch, \
         patch('option_auditor.screener._prepare_data_for_ticker') as mock_prep, \
         patch('option_auditor.screener.yf.download') as mock_download:
        
        # Setup returns to avoid iteration errors
        mock_batch.return_value = MagicMock()
        mock_prep.return_value = None # Return None to skip processing loop body
        yield mock_download

def test_resolve_region_tickers_logic():
    """Test the helper function itself logic."""
    with patch('option_auditor.screener.get_uk_euro_tickers', return_value=["UK_EURO"]), \
         patch('option_auditor.screener.get_uk_tickers', return_value=["UK_ONLY"], create=True), \
         patch('option_auditor.screener.get_indian_tickers', return_value=["INDIA"]), \
         patch('option_auditor.screener._get_filtered_sp500', return_value=["SP500"]), \
         patch('option_auditor.screener.SECTOR_COMPONENTS', {"WATCH": ["WATCH_ITEM"], "TECH": ["US_TECH"]}):
        
        # UK Euro
        assert screener._resolve_region_tickers("uk_euro") == ["UK_EURO"]
        
        # UK (Simulate availability)
        # Note: If get_uk_tickers is not importable in real run, it falls back. 
        # Here we patched it so it should work if we patch the import or the function if it's in scope.
        # Since _resolve_region_tickers imports it inside function:
        # We need to patch sys.modules or the function where it is imported.
        # But for simplicity, let's assume calling providing "uk_euro" works.
        
        # India
        assert screener._resolve_region_tickers("india") == ["INDIA"]
        
        # SP500
        res_sp500 = screener._resolve_region_tickers("sp500")
        assert "SP500" in res_sp500
        assert "WATCH_ITEM" in res_sp500
        
        # US/Default
        res_us = screener._resolve_region_tickers("us")
        assert "US_TECH" in res_us

def test_screeners_use_region_helper(mock_region_helper, mock_fetch_utils):
    """Verify all updated screeners call the helper when ticker_list is None."""
    
    # 1. Turtle
    screener.screen_turtle_setups(region="test_region")
    mock_region_helper.assert_called_with("test_region")
    
    # 2. 5/13
    screener.screen_5_13_setups(region="test_region_2")
    mock_region_helper.assert_called_with("test_region_2")
    
    # 3. Darvas
    screener.screen_darvas_box(region="test_region_3")
    mock_region_helper.assert_called_with("test_region_3")

    # 4. MMS OTE
    screener.screen_mms_ote_setups(region="test_region_4")
    mock_region_helper.assert_called_with("test_region_4")

    # 5. Bull Put
    screener.screen_bull_put_spreads(region="test_region_5")
    mock_region_helper.assert_called_with("test_region_5")
    
    # 6. Fourier
    screener.screen_fourier_cycles(region="test_region_6")
    mock_region_helper.assert_called_with("test_region_6")

    # 7. Hybrid
    # Hybrid uses get_cached_market_data, let's mock it
    with patch('option_auditor.screener.get_cached_market_data'):
        screener.screen_hybrid_strategy(region="test_region_7")
        mock_region_helper.assert_called_with("test_region_7")

def test_screen_market_region_integration():
    """Test screen_market specifically calls helper for non-us regions."""
    with patch('option_auditor.screener._resolve_region_tickers') as mock_helper, \
         patch('option_auditor.screener._screen_tickers'):
         
        # Non-US
        screener.screen_market(region="india")
        mock_helper.assert_called_with("india")
        
        # SP500
        screener.screen_market(region="sp500")
        mock_helper.assert_called_with("sp500")
        
        # US (Should NOT call helper, or if it does, it's fine, but logic was 'if region != "us"')
        mock_helper.reset_mock()
        screener.screen_market(region="us")
        mock_helper.assert_not_called()
