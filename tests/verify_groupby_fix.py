
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock pykalman, pybreaker, and pandas_ta
sys.modules['pykalman'] = MagicMock()
sys.modules['pybreaker'] = MagicMock()
sys.modules['pandas_ta'] = MagicMock()

from option_auditor.screener import _get_filtered_sp500

def test_get_filtered_sp500_multiindex_fix():
    """
    Verifies that _get_filtered_sp500 can handle MultiIndex data 
    without using the deprecated groupby(axis=1).
    """
    # Create a MultiIndex DataFrame similar to yfinance download result
    # We need 20 days of data + 200 for trend
    dates = pd.date_range(start='2022-01-01', periods=300)
    
    # Ticker 1: valid (Vol > 500k, Price > SMA200)
    df1 = pd.DataFrame({
        'Close': [200] * 300,
        'Volume': [600000] * 300
    }, index=dates)
    
    # Ticker 2: invalid volume
    df2 = pd.DataFrame({
        'Close': [100] * 300,
        'Volume': [1000] * 300
    }, index=dates)
    
    # Combine into MultiIndex
    data = pd.concat([df1, df2], axis=1, keys=['AAPL', 'TSLA'])
    # Ensure MultiIndex
    print(f"Data columns: {data.columns}")
    
    with patch('option_auditor.screener.get_sp500_tickers', return_value=['AAPL', 'TSLA']), \
         patch('option_auditor.screener.get_cached_market_data', return_value=data):
         
        print("Calling _get_filtered_sp500 with MultiIndex data...")
        try:
            result = _get_filtered_sp500(check_trend=True)
            print(f"Result: {result}")
            
            assert 'AAPL' in result
            assert 'TSLA' not in result
            print("SUCCESS: Function executed and logic worked!")
            
        except TypeError as e:
            if "unexpected keyword argument 'axis'" in str(e):
                pytest.fail("FAILED: Still getting groupby(axis=1) error!")
            else:
                pytest.fail(f"FAILED: Unexpected TypeError: {e}")
        except Exception as e:
            pytest.fail(f"FAILED: Unexpected Error: {e}")

if __name__ == "__main__":
    test_get_filtered_sp500_multiindex_fix()
