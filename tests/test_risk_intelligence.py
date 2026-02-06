import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.risk_intelligence import calculate_correlation_matrix, get_market_regime

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

@patch('option_auditor.risk_intelligence.fetch_batch_data_safe')
def test_calculate_correlation_short_history(mock_fetch):
    # Create data with only 10 days
    mock_df = create_mock_multiindex_data(['AAPL', 'MSFT'], length=10)
    mock_fetch.return_value = mock_df

    result = calculate_correlation_matrix(['AAPL', 'MSFT'])

    assert "error" in result
    assert "Insufficient overlapping history" in result["error"]

@patch('option_auditor.risk_intelligence.fetch_batch_data_safe')
def test_calculate_correlation_fetch_error(mock_fetch):
    mock_fetch.side_effect = Exception("API Down")

    result = calculate_correlation_matrix(['AAPL', 'MSFT'])

    assert "error" in result
    assert "API Down" in result["error"]

@patch('option_auditor.risk_intelligence.fetch_batch_data_safe')
def test_calculate_correlation_missing_columns(mock_fetch):
    # Create data but without 'Adj Close' or 'Close'
    dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
    df = pd.DataFrame({
        ('AAPL', 'Open'): np.random.randn(50),
        ('MSFT', 'Open'): np.random.randn(50)
    }, index=dates)

    mock_fetch.return_value = df

    result = calculate_correlation_matrix(['AAPL', 'MSFT'])

    assert "error" in result
    assert "Could not extract prices" in result["error"]

def test_calculate_correlation_no_tickers():
    result = calculate_correlation_matrix(None)
    assert "error" in result
    assert "No tickers" in result["error"]

# --- Market Regime Tests ---

def _create_base_df(length=250):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')
    return pd.DataFrame({
        'Close': [100.0] * length,
        'High': [101.0] * length,
        'Low': [99.0] * length
    }, index=dates)

@patch('option_auditor.risk_intelligence._calculate_atr')
@patch('option_auditor.risk_intelligence._calculate_rsi')
def test_market_regime_stormy(mock_rsi, mock_atr):
    df = _create_base_df()

    # ATR Spike at the end
    # History: 1.0, Current: 10.0
    atr_vals = [1.0] * (len(df)-1) + [10.0]
    mock_atr.return_value = pd.Series(atr_vals, index=df.index)

    mock_rsi.return_value = pd.Series([50.0] * len(df), index=df.index)

    result = get_market_regime(df)
    assert result == "Stormy (High Risk)"

@patch('option_auditor.risk_intelligence._calculate_atr')
@patch('option_auditor.risk_intelligence._calculate_rsi')
def test_market_regime_bearish(mock_rsi, mock_atr):
    df = _create_base_df()

    # Normal ATR
    mock_atr.return_value = pd.Series([1.0] * len(df), index=df.index)
    mock_rsi.return_value = pd.Series([50.0] * len(df), index=df.index)

    # Price < SMA 200
    # SMA of [100...] is 100.
    # Set current close to 90
    df.iloc[-1, df.columns.get_loc('Close')] = 90.0

    result = get_market_regime(df)
    assert result == "Bearish (Caution)"

@patch('option_auditor.risk_intelligence._calculate_atr')
@patch('option_auditor.risk_intelligence._calculate_rsi')
def test_market_regime_bullish(mock_rsi, mock_atr):
    df = _create_base_df()

    # Normal ATR
    mock_atr.return_value = pd.Series([1.0] * len(df), index=df.index)

    # High RSI
    mock_rsi.return_value = pd.Series([60.0] * len(df), index=df.index)

    # Price > SMA 200
    df.iloc[-1, df.columns.get_loc('Close')] = 110.0
    # SMA will still be roughly 100 (avg of 249*100 + 110 approx 100)

    result = get_market_regime(df)
    assert result == "Bullish (Safe)"

@patch('option_auditor.risk_intelligence._calculate_atr')
@patch('option_auditor.risk_intelligence._calculate_rsi')
def test_market_regime_neutral(mock_rsi, mock_atr):
    df = _create_base_df()

    # Normal ATR
    mock_atr.return_value = pd.Series([1.0] * len(df), index=df.index)

    # Low RSI
    mock_rsi.return_value = pd.Series([40.0] * len(df), index=df.index)

    # Price > SMA 200
    df.iloc[-1, df.columns.get_loc('Close')] = 110.0

    result = get_market_regime(df)
    assert result == "Neutral (Sideways)"

def test_market_regime_insufficient_data():
    df = _create_base_df(length=50) # Too short
    result = get_market_regime(df)
    assert "Insufficient History" in result

def test_market_regime_missing_columns():
    df = pd.DataFrame({'Close': [100]*250})
    result = get_market_regime(df)
    assert "Missing Columns" in result

def test_market_regime_empty():
    result = get_market_regime(pd.DataFrame())
    assert "No Data" in result
