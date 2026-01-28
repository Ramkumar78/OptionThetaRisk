import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from option_auditor.screener import screen_dynamic_volatility_fortress

@pytest.fixture
def mock_yfinance(monkeypatch):
    mock = MagicMock()
    # Updated path: yf is used in common.screener_utils for _get_market_regime
    monkeypatch.setattr("option_auditor.common.screener_utils.yf", mock)
    # Mock VIX download
    vix_df = pd.DataFrame({'Close': [16.0]}, index=[pd.Timestamp.now()])
    mock.download.return_value = vix_df
    return mock

@pytest.fixture
def mock_get_cached_data(monkeypatch):
    mock = MagicMock()
    # Updated path: get_cached_market_data is imported in strategies.fortress
    monkeypatch.setattr("option_auditor.strategies.fortress.get_cached_market_data", mock)
    return mock

def test_screen_fortress_logic(mock_yfinance, mock_get_cached_data):
    # Setup mock data for a ticker
    # We need Close, High, Low for ATR and SMA calculations
    dates = pd.date_range(end=pd.Timestamp.now(), periods=201)
    df = pd.DataFrame({
        'Close': [100.0] * 201,
        'High': [102.0] * 201,
        'Low': [98.0] * 201,
        'Open': [100.0] * 201,
        'Volume': [1000000] * 201
    }, index=dates)

    # Make it a bull trend: Price > 200 SMA
    # Last price 150, SMA 200 ~ 100
    df.iloc[-1, df.columns.get_loc('Close')] = 150.0
    df.iloc[-1, df.columns.get_loc('High')] = 152.0
    df.iloc[-1, df.columns.get_loc('Low')] = 148.0

    # Mock return from get_cached_market_data
    # It returns a MultiIndex DataFrame usually, or single if one ticker
    # screen_dynamic_volatility_fortress handles MultiIndex

    # Let's mock a MultiIndex return for "AAPL"
    tuples = [("AAPL", col) for col in df.columns]
    multi_index = pd.MultiIndex.from_tuples(tuples)
    multi_df = pd.DataFrame(df.values, index=dates, columns=multi_index)

    mock_get_cached_data.return_value = multi_df

    # Run Screener
    results = screen_dynamic_volatility_fortress(ticker_list=["AAPL"])

    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == "AAPL"
    assert res['trend'] == "Bullish"
    # Check safety_mult (returned as string "1.8x")
    safety_val = float(res['safety_mult'].replace('x', ''))
    assert safety_val >= 1.5

    # Check Math
    # ATR approx 4.0? High-Low=4.0 usually in mock, plus gap?
    # SMA 20 approx 100 (mostly 100s)
    # Price 150
    # Strike = SMA_20 - (K * ATR)
    # If SMA20 ~ 100, Strike < 100.
    # Price 150. Cushion should be large.

    assert res['sell_strike'] < res['price']
    assert res['buy_strike'] < res['sell_strike']

def test_screen_fortress_bearish_filter(mock_yfinance, mock_get_cached_data):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=201)
    df = pd.DataFrame({
        'Close': [200.0] * 200 + [100.0], # Crash to 100, SMA 200 ~ 200
        'High': [205.0] * 201,
        'Low': [195.0] * 201,
        'Volume': [1000000] * 201
    }, index=dates)

    tuples = [("TSLA", col) for col in df.columns]
    multi_index = pd.MultiIndex.from_tuples(tuples)
    multi_df = pd.DataFrame(df.values, index=dates, columns=multi_index)

    mock_get_cached_data.return_value = multi_df

    results = screen_dynamic_volatility_fortress(ticker_list=["TSLA"])

    # Should be filtered out because Price < SMA 200
    assert len(results) == 0
