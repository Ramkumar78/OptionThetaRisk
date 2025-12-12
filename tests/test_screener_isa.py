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
