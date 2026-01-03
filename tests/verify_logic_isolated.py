
import pandas as pd
import pytest

def test_manual_iteration_logic():
    """
    Verifies that the replacement logic for groupby(axis=1) works as expected.
    """
    # Create a MultiIndex DataFrame
    tuples = [('AAPL', 'Close'), ('AAPL', 'Volume'), ('TSLA', 'Close'), ('TSLA', 'Volume')]
    index = pd.MultiIndex.from_tuples(tuples, names=['Ticker', 'Price'])
    data = pd.DataFrame({'a': [1, 2], 'b': [3, 4], 'c': [5, 6], 'd': [7, 8]}, columns=index)
    
    # 1. Test iteration
    print("Iterating...")
    count = 0
    tickers_found = []
    
    if isinstance(data.columns, pd.MultiIndex):
        iterator = [(ticker, data[ticker]) for ticker in data.columns.unique(level=0)]
        for ticker, df in iterator:
            print(f"Ticker: {ticker}")
            print(f"Columns: {df.columns}")
            print(f"Shape: {df.shape}")
            
            tickers_found.append(ticker)
            count += 1
            
            # Verify columns are single level now
            assert not isinstance(df.columns, pd.MultiIndex)
            assert 'Close' in df.columns or 'Volume' in df.columns
            
    assert count == 2
    assert 'AAPL' in tickers_found
    assert 'TSLA' in tickers_found
    print("SUCCESS: Logic works!")

if __name__ == "__main__":
    test_manual_iteration_logic()
