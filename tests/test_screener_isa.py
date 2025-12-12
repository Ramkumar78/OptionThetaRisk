
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
    # Setup mock data: Bullish Trend (>SMA200) and Breakout (>50d High)
    dates = pd.date_range(start='2022-01-01', periods=300)

    # Create a rising price series
    prices = np.linspace(100, 200, 300)
    # Add a spike at the end to trigger breakout
    prices[-1] = 205

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    # Mock return value needs to be a DataFrame (single ticker) or MultiIndex (multi ticker)
    # The screener calls download with group_by='ticker'
    # So it expects MultiIndex if multiple tickers, or usually returns MultiIndex anyway with group_by.
    # Let's mock a MultiIndex return for "AAPL"

    tuples = [("AAPL", col) for col in df.columns]
    columns = pd.MultiIndex.from_tuples(tuples)
    df_multi = pd.DataFrame(df.values, index=df.index, columns=columns)

    mock_yf_download.return_value = df_multi

    # Run Screener with just AAPL to simplify
    results = screen_trend_followers_isa(ticker_list=["AAPL"])

    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == "AAPL"
    assert "ENTER LONG" in res['signal']
    assert res['trend_200sma'] == "Bullish"
    assert res['stop_loss_3atr'] < res['price']

def test_screen_trend_followers_isa_downtrend(mock_yf_download):
    # Setup mock data: Bearish Trend (<SMA200)
    dates = pd.date_range(start='2022-01-01', periods=300)

    # Create a falling price series
    prices = np.linspace(200, 100, 300)

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    tuples = [("TSLA", col) for col in df.columns]
    columns = pd.MultiIndex.from_tuples(tuples)
    df_multi = pd.DataFrame(df.values, index=df.index, columns=columns)

    mock_yf_download.return_value = df_multi

    results = screen_trend_followers_isa(ticker_list=["TSLA"])

    # Should be empty or filtered out (AVOID signals are skipped in code)
    assert len(results) == 0

def test_screen_trend_followers_isa_hold(mock_yf_download):
    # Setup mock data: Bullish Trend (>SMA200) but not breakout (Price < 50d High)
    dates = pd.date_range(start='2022-01-01', periods=300)

    # Rising then flat
    prices = np.linspace(100, 150, 250) # Rise
    prices = np.concatenate([prices, np.linspace(150, 145, 50)]) # Pullback

    # Ensure current close > SMA 200
    # SMA 200 approx average of last 200.

    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 2,
        'Low': prices - 2,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)

    tuples = [("MSFT", col) for col in df.columns]
    columns = pd.MultiIndex.from_tuples(tuples)
    df_multi = pd.DataFrame(df.values, index=df.index, columns=columns)

    mock_yf_download.return_value = df_multi

    results = screen_trend_followers_isa(ticker_list=["MSFT"])

    assert len(results) == 1
    res = results[0]
    assert "HOLD" in res['signal'] or "WATCH" in res['signal']
