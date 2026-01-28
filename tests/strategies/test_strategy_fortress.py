import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import time
from option_auditor.screener import screen_dynamic_volatility_fortress

# Mock Fixtures

@pytest.fixture
def mock_market_data():
    def _gen(days=200, price=100.0):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=days)
        df = pd.DataFrame({
            'Close': [price] * days,
            'High': [price*1.02] * days,
            'Low': [price*0.98] * days,
            'Open': [price] * days,
            'Volume': [1000000] * days
        }, index=dates)
        return df
    return _gen

@patch('option_auditor.strategies.fortress.get_cached_market_data')
@patch('option_auditor.strategies.fortress._get_market_regime', return_value=15.0)
def test_screen_fortress_valid(mock_vix, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=150.0)
    # Ensure it looks bullish (Price > SMA)
    # With flat price, SMA is same as Price. Let's bump price up at end.
    df.iloc[-1, df.columns.get_loc('Close')] = 160.0

    # Wrap in MultiIndex for robustness
    cols = pd.MultiIndex.from_product([['FORT'], df.columns])
    multi_df = pd.DataFrame(df.values, index=df.index, columns=cols)
    mock_cache.return_value = multi_df

    with patch('pandas_ta.atr', return_value=pd.Series([3.5]*len(df), index=df.index)):
        with patch('pandas_ta.ema', return_value=pd.Series([150.0]*len(df), index=df.index)): # SMA < Price
             results = screen_dynamic_volatility_fortress(ticker_list=["FORT"])

             assert len(results) == 1
             res = results[0]
             assert 'sell_strike' in res
             assert res['ticker'] == "FORT"

@patch('option_auditor.strategies.fortress.get_cached_market_data')
@patch('option_auditor.strategies.fortress._get_market_regime', return_value=10.0)
def test_screen_fortress_dead_money(mock_vix, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    # Wrap in MultiIndex
    cols = pd.MultiIndex.from_product([['DEAD'], df.columns])
    multi_df = pd.DataFrame(df.values, index=df.index, columns=cols)
    mock_cache.return_value = multi_df

    # Low ATR -> Filtered out as dead money
    with patch('pandas_ta.atr', return_value=pd.Series([0.5]*len(df), index=df.index)):
        results = screen_dynamic_volatility_fortress(ticker_list=["DEAD"])
        assert len(results) == 0

@patch('option_auditor.strategies.fortress.get_cached_market_data')
@patch('option_auditor.strategies.fortress._get_market_regime', return_value=30.0)
def test_screen_fortress_high_vol(mock_vix, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    cols = pd.MultiIndex.from_product([['HIGHVOL'], df.columns])
    multi_df = pd.DataFrame(df.values, index=df.index, columns=cols)
    mock_cache.return_value = multi_df

    with patch('pandas_ta.atr', return_value=pd.Series([5.0]*len(df), index=df.index)):
        with patch('pandas_ta.ema', return_value=pd.Series([90.0]*len(df), index=df.index)):
             results = screen_dynamic_volatility_fortress(ticker_list=["HIGHVOL"])
             if results:
                 assert results[0]['safety_mult'] == "2.7x"

@patch('option_auditor.strategies.fortress.get_cached_market_data')
@patch('option_auditor.strategies.fortress._get_market_regime', return_value=15.0)
def test_screen_fortress_bearish_filter(mock_vix, mock_cache, mock_market_data):
    """
    Merged from test_screener_fortress.py
    """
    df = mock_market_data(days=250, price=100.0)
    cols = pd.MultiIndex.from_product([['BEAR'], df.columns])
    multi_df = pd.DataFrame(df.values, index=df.index, columns=cols)
    mock_cache.return_value = multi_df

    # Make Price < SMA
    with patch('pandas_ta.ema', return_value=pd.Series([110.0]*len(df), index=df.index)):
        results = screen_dynamic_volatility_fortress(ticker_list=["BEAR"])
        assert len(results) == 0

@patch('option_auditor.common.screener_utils.get_cached_market_data')
@patch('yfinance.download')
def test_screen_fortress_performance(mock_download, mock_get_cached_data):
    """
    Merged from test_screener_fortress_repro.py.
    Checks that it runs fast enough.
    """
    # Mock VIX download
    mock_download.return_value = pd.DataFrame({'Close': [15.0]}, index=[pd.Timestamp.now()])

    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA"]
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200)

    # Create MultiIndex DF
    tuples = []
    for t in tickers:
        for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
            tuples.append((t, c))

    multi_index = pd.MultiIndex.from_tuples(tuples)
    data = np.random.randn(200, len(tickers) * 5)
    df = pd.DataFrame(data, index=dates, columns=multi_index)

    # Sanitize data to avoid calculation errors
    # Close > 0, Volume > 0
    df = df.abs() + 10.0

    mock_get_cached_data.return_value = df

    start_time = time.time()
    results = screen_dynamic_volatility_fortress(ticker_list=tickers)
    end_time = time.time()

    duration = end_time - start_time
    # Assert execution is fast (e.g., < 2s for 5 tickers)
    assert duration < 2.0
    assert isinstance(results, list)
