import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy

@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.math_utils.calculate_dominant_cycle')
def test_screen_hybrid_strategy_uk_euro(mock_cycle, mock_get_data):
    # Setup mock data for indicators
    # We need enough data for rolling(200), rolling(50), etc.
    # Create 250 days of data
    dates = pd.date_range(start='2023-01-01', periods=250)
    
    # Create a bullish trend: Price constantly increasing
    closes = np.linspace(100, 200, 250)
    highs = closes + 5
    lows = closes - 5
    opens = closes - 2
    volumes = [1000000] * 250 # High volume to pass filters

    mock_df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)

    # Mock return values
    # Return a MultiIndex DataFrame as yfinance often does for multiple tickers, 
    # OR a dictionary if get_cached_market_data returns dict (it usually returns dict or DF depending on implementation).
    # Looking at screener.py, get_cached_market_data returns a DataFrame where columns might be MultiIndex.
    # But let's look at usage: 
    # if isinstance(all_data.columns, pd.MultiIndex): ...
    
    # Let's verify what get_cached_market_data returns. 
    # In screener.py: all_data = get_cached_market_data(...)
    # Then it checks if MultiIndex.
    
    # We will construct a MultiIndex DataFrame to mimic batch fetch
    # Tickers: AZN.L, SHEL.L
    
    # Construct MultiIndex columns: (Ticker, PriceField)
    arrays = [
        ['AZN.L']*5 + ['SHEL.L']*5,
        ['Open', 'High', 'Low', 'Close', 'Volume'] * 2
    ]
    # This is complicated to construct manually perfectly matching yf.
    
    # Alternative: The screener handles flat DF if only 1 ticker?
    # But we want to test multiple.
    
    # Let's just use the fact that get_cached_market_data MIGHT return a dict of DFs if we mock it that way?
    # No, screener.py expects a DataFrame with MultiIndex for multiple tickers.
    
    # Easier: Mock `fetch_batch_data_safe`? No, screen_hybrid_strategy calls `get_cached_market_data`.
    
    # Let's create a MultiIndex DataFrame
    iterables = [['AZN.L', 'SHEL.L'], ['Open', 'High', 'Low', 'Close', 'Volume']]
    index = pd.MultiIndex.from_product(iterables, names=['Ticker', 'Price'])
    
    # Create data frame with 250 rows, columns=MultiIndex
    data_values = np.tile(mock_df.values, (1, 2)) # Duplicate data for 2 tickers (but shape mismatch?)
    # mock_df has 5 cols. MultiIndex has 10 cols.
    
    # Reshape mock_df values to match consumption?
    # Actually, simpler way:
    # Just return a DataFrame where columns are MultiIndex
    
    df_combined = pd.DataFrame(index=dates)
    for ticker in ['AZN.L', 'SHEL.L']:
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df_combined[(ticker, col)] = mock_df[col]
            
    df_combined.columns = pd.MultiIndex.from_tuples(df_combined.columns)
    
    mock_get_data.return_value = df_combined
    
    # Mock Cycle to return "BOTTOM" signal (rel_pos <= -0.7)
    # _calculate_dominant_cycle returns (period, rel_pos)
    mock_cycle.return_value = (20, -0.8) # -0.8 is <= -0.7 -> BOTTOM

    # Test execution
    results = screen_hybrid_strategy(region="uk_euro", time_frame="1d")

    # Verification
    # 1. Verify correct cache key was used indicating region awareness
    mock_get_data.assert_called()
    call_args = mock_get_data.call_args
    assert call_args.kwargs.get('cache_name') == 'market_scan_europe'
    
    # 2. Results should contain our tickers since they match Bullish Trend + Cycle Bottom
    # Logic: Close (200) > SMA200 (~150). Trend = BULLISH.
    # Cycle = BOTTOM (-0.8).
    # Result: "PERFECT BUY" or similar.
    
    assert len(results) > 0
    found_tickers = [r['ticker'] for r in results]
    assert 'AZN.L' in found_tickers or 'SHEL.L' in found_tickers
