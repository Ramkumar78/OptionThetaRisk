
import pandas as pd
import pytest
from option_auditor.screener import _get_filtered_sp500

def test_groupby_axis_failure():
    """
    Simulates the failure by attempting to use groupby(level=0, axis=1)
    on a MultiIndex DataFrame, mimicking the pattern in screener.py.
    """
    # Create a MultiIndex DataFrame similar to yfinance download result
    tuples = [('AAPL', 'Close'), ('AAPL', 'Volume'), ('MSFT', 'Close'), ('MSFT', 'Volume')]
    index = pd.MultiIndex.from_tuples(tuples, names=['Ticker', 'Price'])
    data = pd.DataFrame({'a': [1, 2], 'b': [3, 4], 'c': [5, 6], 'd': [7, 8]}, columns=index)
    
    print("Attempting deprecated groupby(axis=1)...")
    try:
        # This is the exact line causing issues in the codebase
        for ticker, df in data.groupby(level=0, axis=1):
            print(f"Ticker: {ticker}, Shape: {df.shape}")
        print("SUCCESS: groupby(axis=1) worked (unexpected if using new pandas)")
    except TypeError as e:
        print(f"CAUGHT EXPECTED ERROR: {e}")
        assert "unexpected keyword argument 'axis'" in str(e)
    except Exception as e:
        print(f"CAUGHT UNEXPECTED ERROR: {e}")
        # If it's another error, we might still want to fail or just note it
        raise e

if __name__ == "__main__":
    test_groupby_axis_failure()
