import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from option_auditor.risk_intelligence import calculate_correlation_matrix

def create_mock_multiindex_data(tickers, length=50):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    # Create random correlated data
    data = {}
    base = np.linspace(100, 200, length)

    for t in tickers:
        noise = np.random.normal(0, 5, length)
        prices = base + noise
        # Columns for this ticker
        df = pd.DataFrame({
            'Open': prices,
            'High': prices+1,
            'Low': prices-1,
            'Close': prices,
            'Adj Close': prices,
            'Volume': 1000
        }, index=dates)
        data[t] = df

    # Combine into MultiIndex: (Ticker, PriceType) ? No, yfinance usually (PriceType, Ticker) OR (Ticker, PriceType)
    # fetch_batch_data_safe uses group_by='ticker', so it's (Ticker, PriceType)

    # Concatenate along axis 1
    # Keys for concat will form the top level
    df = pd.concat(data.values(), axis=1, keys=data.keys())
    return df

@patch('option_auditor.risk_intelligence.fetch_batch_data_safe')
def test_calculate_correlation_matrix_success(mock_fetch):
    tickers = ['AAPL', 'MSFT', 'GOOG']
    mock_df = create_mock_multiindex_data(tickers)
    mock_fetch.return_value = mock_df

    result = calculate_correlation_matrix(tickers)

    assert "error" not in result
    assert "matrix" in result
    assert len(result["matrix"]) == 3
    assert len(result["tickers"]) == 3
    assert result["tickers"] == sorted(tickers) # Should be sorted by default logic

    # Correlation of a variable with itself is 1.0
    # Matrix is list of lists.
    # Check diagonal
    for i in range(3):
        assert result["matrix"][i][i] == 1.0

@patch('option_auditor.risk_intelligence.fetch_batch_data_safe')
def test_calculate_correlation_insufficient_data(mock_fetch):
    mock_fetch.return_value = pd.DataFrame() # Empty

    result = calculate_correlation_matrix(['AAPL', 'MSFT'])
    assert "error" in result
    assert "No data" in result["error"]

def test_calculate_correlation_single_ticker():
    result = calculate_correlation_matrix(['AAPL'])
    assert "error" in result
    assert "least 2 tickers" in result["error"]
