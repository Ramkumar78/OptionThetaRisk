import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from option_auditor.screener import screen_hybrid_strategy
from option_auditor.uk_stock_data import get_uk_tickers

@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener._calculate_dominant_cycle')
def test_screen_hybrid_uk_350_logic(mock_cycle, mock_get_data):
    # Setup Mocks
    mock_cycle.return_value = (20, 0.0) # Bottom
    
    # We don't strictly need valid data returned if we just check the call args, 
    # but let's provide minimal structure to avoid crashes.
    mock_df = pd.DataFrame({
        'Close': [100.0] * 50,
        'High': [105.0] * 50,
        'Low': [95.0] * 50,
        'Volume': [1000] * 50
    })
    # Return empty DF or minimal DF to satisfy variable assignment
    # screen_hybrid checks `isinstance(all_data.columns, pd.MultiIndex)`
    # We can just return an empty DF if we only care about the *call* to get_cached_market_data
    mock_get_data.return_value = pd.DataFrame() 

    # Execution
    results = screen_hybrid_strategy(region="uk", time_frame="1d")

    # Verification 1: Cache Key
    mock_get_data.assert_called()
    call_args = mock_get_data.call_args
    assert call_args.kwargs.get('cache_name') == 'market_scan_uk'
    
    # Verification 2: Ticker List
    # The passed ticker list should match get_uk_tickers()
    passed_tickers = call_args.args[0] if call_args.args else call_args.kwargs.get('tickers')
    assert len(passed_tickers) >= 150 # Should be basically the full list
    assert "SHEL.L" in passed_tickers
    assert "AZN.L" in passed_tickers
    assert passed_tickers == get_uk_tickers()

def test_uk_350_data_integrity():
    # Verify the file `uk_stock_data.py` is valid
    uk_tickers = get_uk_tickers()
    assert len(uk_tickers) >= 150
    assert all(t.endswith('.L') or 'BRK' in t for t in uk_tickers if '.L' in t) # Check for .L mainly
    # Note: Some tickers might be exceptions like BRK-B if scraped from UK site but globally listed? 
    # But filters were LSE. Let's rely on majority check.
    l_suffixes = [t for t in uk_tickers if t.endswith('.L')]
    assert len(l_suffixes) > 150 # Most should be .L
