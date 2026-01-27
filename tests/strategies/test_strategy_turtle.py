import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.screener import screen_turtle_setups

# --- Class-Based Strategy Tests (option_auditor/strategies/turtle.py) ---

class TestTurtleStrategyClass:

    def test_turtle_breakout_buy(self, mock_market_data):
        # Create data with a clear breakout
        # 20 days flat then jump
        df = mock_market_data(days=30, price=100.0, trend="flat")
        # Make the last price jump above the previous 20-day high
        high_20 = df['High'].rolling(20).max().shift(1).iloc[-1]
        df.iloc[-1, df.columns.get_loc('Close')] = high_20 + 5.0 # Breakout
        df.iloc[-1, df.columns.get_loc('High')] = high_20 + 6.0

        strategy = TurtleStrategy("TEST", df)
        result = strategy.analyze()

        assert "BREAKOUT (BUY)" in result['signal']

    def test_turtle_breakdown_sell(self, mock_market_data):
        df = mock_market_data(days=30, price=100.0, trend="flat")
        # Make the last price drop below previous 20-day low
        low_20 = df['Low'].rolling(20).min().shift(1).iloc[-1]
        df.iloc[-1, df.columns.get_loc('Close')] = low_20 - 5.0 # Breakdown
        df.iloc[-1, df.columns.get_loc('Low')] = low_20 - 6.0

        strategy = TurtleStrategy("TEST", df)
        result = strategy.analyze()

        assert "BREAKDOWN (SELL)" in result['signal']

    def test_turtle_wait(self, mock_market_data):
        df = mock_market_data(days=30, price=100.0, trend="flat")
        # Price within range but not near high (avoid WATCH)
        # Assuming previous high is ~100
        high_20 = df['High'].rolling(20).max().shift(1).iloc[-1]
        df.iloc[-1, df.columns.get_loc('Close')] = high_20 * 0.95

        strategy = TurtleStrategy("TEST", df)
        result = strategy.analyze()

        # The new strategy returns None if signal is WAIT and check_mode is False
        assert result is None

    def test_turtle_insufficient_data(self, mock_market_data):
        df = mock_market_data(days=10)
        strategy = TurtleStrategy("TEST", df)
        result = strategy.analyze()
        assert result is None

# --- Functional Screener Tests (option_auditor/screener.py - screen_turtle_setups) ---

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('option_auditor.common.screener_utils.get_cached_market_data')
@patch('option_auditor.common.constants.TICKER_NAMES', {"AAPL": "Apple Inc."})
def test_screen_turtle_setups_breakout(mock_get_cache, mock_fetch, mock_market_data):
    # Setup mock data with breakout
    df = mock_market_data(days=50, price=100.0, trend="flat")

    # Create valid Donchian channels
    df['High'] = 100.0
    df['Low'] = 90.0
    df['Close'] = 95.0

    # 20 day high was 100. Last close is 105.
    df.iloc[-1, df.columns.get_loc('Close')] = 105.0

    # Mock data return. Important: patch where ScreeningRunner imports it from.
    # ScreeningRunner is in option_auditor.common.screener_utils
    with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=df):
        results = screen_turtle_setups(ticker_list=["AAPL"], region="us")

        assert len(results) == 1
        res = results[0]
        assert "BREAKOUT (BUY)" in res['signal']
        assert res['ticker'] == "AAPL"
        assert res['price'] == 105.0

@patch('option_auditor.common.screener_utils.prepare_data_for_ticker')
def test_screen_turtle_setups_breakdown(mock_prepare):
    # Setup data
    dates = pd.date_range(end=datetime.now(), periods=50)
    df = pd.DataFrame({
        'Open': 100.0, 'High': 100.0, 'Low': 90.0, 'Close': 95.0, 'Volume': 1000000
    }, index=dates)

    # 20 day low was 90. Last close is 85.
    df.iloc[-1, df.columns.get_loc('Close')] = 85.0

    mock_prepare.return_value = df

    results = screen_turtle_setups(ticker_list=["TSLA"])

    assert len(results) == 1
    assert "BREAKDOWN (SELL)" in results[0]['signal']
    assert results[0]['target'] < 85.0 # Target lower for short

@patch('option_auditor.common.screener_utils.prepare_data_for_ticker')
def test_screen_turtle_near_high(mock_prepare):
    dates = pd.date_range(end=datetime.now(), periods=50)
    df = pd.DataFrame({
        'Open': 100.0, 'High': 100.0, 'Low': 90.0, 'Close': 95.0, 'Volume': 1000000
    }, index=dates)

    # High is 100. Current close is 99 (Near High)
    df.iloc[-1, df.columns.get_loc('Close')] = 99.0

    mock_prepare.return_value = df

    results = screen_turtle_setups(ticker_list=["NVDA"])

    assert len(results) == 1
    assert "WATCH" in results[0]['signal']

@patch('option_auditor.common.screener_utils.prepare_data_for_ticker')
def test_screen_turtle_empty_data(mock_prepare):
    mock_prepare.return_value = None
    results = screen_turtle_setups(ticker_list=["BAD"])
    assert len(results) == 0

@patch('option_auditor.common.screener_utils.resolve_region_tickers')
@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_turtle_region_default(mock_fetch, mock_resolve):
    mock_resolve.return_value = ["AAPL"]
    # We mock fetch to return empty to avoid errors, relying on loop logic
    mock_fetch.return_value = pd.DataFrame()

    # We need to mock _prepare_data_for_ticker inside the loop or ensure data allows it
    with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=None):
        results = screen_turtle_setups(ticker_list=None, region="us")
        assert len(results) == 0
        mock_resolve.assert_called_with("us")
