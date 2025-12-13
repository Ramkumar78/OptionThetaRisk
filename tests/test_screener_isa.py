import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_trend_followers_isa

@pytest.fixture
def mock_yf_download():
    with patch('yfinance.download') as mock:
        yield mock

def test_screen_trend_followers_isa_breakout(mock_yf_download):
    dates = pd.date_range(start='2022-01-01', periods=300)
    prices = np.linspace(100, 200, 300)
    prices[-1] = 205

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    # For single ticker, we expect simple DataFrame
    mock_yf_download.return_value = df

    results = screen_trend_followers_isa(ticker_list=["AAPL"])

    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == "AAPL"
    assert "ENTER LONG" in res['signal']

def test_screen_trend_followers_isa_downtrend(mock_yf_download):
    dates = pd.date_range(start='2022-01-01', periods=300)
    prices = np.linspace(200, 100, 300)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    mock_yf_download.return_value = df

    results = screen_trend_followers_isa(ticker_list=["TSLA"])

    assert len(results) == 1
    assert "SELL/AVOID" in results[0]['signal']

def test_screen_trend_followers_isa_hold(mock_yf_download):
    dates = pd.date_range(start='2022-01-01', periods=300)
    prices = np.linspace(100, 150, 250)
    prices = np.concatenate([prices, np.linspace(150, 145, 50)])

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    mock_yf_download.return_value = df

    results = screen_trend_followers_isa(ticker_list=["MSFT"])

    assert len(results) == 1
    assert "HOLD" in results[0]['signal']

@patch('option_auditor.screener.fetch_data_with_retry')
def test_screen_trend_followers_isa_risk_assessment(mock_fetch):
    # Using fetch_data_with_retry path (single ticker)
    dates = pd.date_range(start='2022-01-01', periods=250)

    # 1. SAFE Case
    # ATR approx 4 (High 102, Low 98)
    # Price 100. Stop ~88 (3*4=12). Dist 12%. Risk 0.12*0.04 = 0.0048 (0.48%) < 1%.
    df_safe = pd.DataFrame({
        'Open': [100.0]*250,
        'High': [102.0]*250,
        'Low': [98.0]*250,
        'Close': [100.0]*250,
        'Volume': [1000000]*250
    }, index=dates)

    mock_fetch.return_value = df_safe
    results = screen_trend_followers_isa(ticker_list=["SAFE_STK"])
    assert len(results) == 1
    assert results[0]['safe_to_trade'] is True
    assert "Yes. Risk is" in results[0]['risk_message']

    # 2. UNSAFE Case
    # ATR approx 10 (High 105, Low 95)
    # Price 100. Stop ~70 (3*10=30). Dist 30%. Risk 0.30*0.04 = 0.012 (1.2%) > 1%.
    df_unsafe = pd.DataFrame({
        'Open': [100.0]*250,
        'High': [105.0]*250,
        'Low': [95.0]*250,
        'Close': [100.0]*250,
        'Volume': [1000000]*250
    }, index=dates)

    mock_fetch.return_value = df_unsafe
    results = screen_trend_followers_isa(ticker_list=["RISKY_STK"])
    assert len(results) == 1
    assert results[0]['safe_to_trade'] is False
    assert "No. Risk is" in results[0]['risk_message']
    assert "(Limit 1%)" in results[0]['risk_message']
