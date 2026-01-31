import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.screener import screen_trend_followers_isa

# --- Class-Based Strategy Tests ---

class TestISAStrategyClass:

    def test_isa_trend_enter(self, mock_market_data):
        # Use enough days for 252-day rolling window
        df = mock_market_data(days=300, price=100.0, trend="up")

        # Ensure SMA 200 condition met (Price > SMA)
        # Ensure 50d High Breakout
        # Set last price to new high
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        df.iloc[-1, df.columns.get_loc('Close')] = high_50 + 2.0

        # Ensure Minervini checks pass (SMA 50 > SMA 200)
        # Mock data trend=up should provide this naturally if linear

        strategy = IsaStrategy("AAPL", df)
        result = strategy.analyze()

        assert "ENTER" in result['signal']
        assert result['breakout_level'] <= result['price']

    def test_isa_trend_watchlist(self, mock_market_data):
        df = mock_market_data(days=300, price=100.0, trend="up")

        # Trend OK, Near Highs, but NOT breaking out
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        df.iloc[-1, df.columns.get_loc('Close')] = high_50 - 2.0

        strategy = IsaStrategy("AAPL", df)
        result = strategy.analyze()

        assert "WATCH" in result['signal']

    def test_isa_trend_bear(self, mock_market_data):
        df = mock_market_data(days=300, price=100.0, trend="down")
        # Price < SMA 200 automatically in strong downtrend mock

        strategy = IsaStrategy("AAPL", df)
        result = strategy.analyze()

        # In a downtrend, signal should be SELL/AVOID
        assert result is not None
        assert "AVOID" in result['signal'] or "SELL" in result['signal']

# --- Functional Screener Tests ---

@patch('option_auditor.common.screener_utils.get_cached_market_data')
@patch('yfinance.download')
def test_screen_isa_liquidity_filter(mock_download, mock_cache, mock_market_data):
    # Test that low volume stocks are filtered out
    df = mock_market_data(days=250, price=10.0)
    df['Volume'] = 1000 # Very low volume

    # Mock return for single ticker
    mock_download.return_value = df

    results = screen_trend_followers_isa(ticker_list=["ILLIQUID"], region="us")
    assert len(results) == 0

@patch('option_auditor.common.screener_utils.get_cached_market_data')
@patch('yfinance.download')
def test_screen_isa_valid_entry(mock_download, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=100.0, trend="up")
    df['Volume'] = 10_000_000 # High volume

    # Force breakout
    high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
    df.iloc[-1, df.columns.get_loc('Close')] = high_50 + 1.0

    mock_download.return_value = df

    results = screen_trend_followers_isa(ticker_list=["AAPL"], region="us")

    assert len(results) == 1
    assert "ENTER LONG" in results[0]['signal']
    assert results[0]['safe_to_trade'] is True # Assuming default risk calc

@patch('option_auditor.common.screener_utils.get_cached_market_data')
def test_screen_isa_risk_management(mock_cache, mock_market_data):
    # Test Tharp verdict (Position Sizing)
    df = mock_market_data(days=250, price=100.0, trend="up")
    df['Volume'] = 10_000_000

    # Create a huge volatility condition (Wide stop)
    # Stop is 3*ATR. If ATR is huge, risk is huge.

    # Let's force a breakout but with logic to check output
    high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
    df.iloc[-1, df.columns.get_loc('Close')] = high_50 + 1.0

    mock_cache.return_value = df # Usually expects MultiIndex if list > 50, but for single it handles

    # We patch yf.download inside too if list < 50
    with patch('yfinance.download', return_value=df):
        results = screen_trend_followers_isa(ticker_list=["RISKY"])

        assert len(results) == 1
        res = results[0]
        assert 'stop_loss' in res
        assert 'max_position_size' in res
        assert 'tharp_verdict' in res

def test_isa_invalid_input():
    # Test bad risk parameter clamping
    with patch('option_auditor.screener.logger') as mock_logger:
        screen_trend_followers_isa(ticker_list=[], risk_per_trade_pct=0.5) # Too high
        # We expect a warning log or just safe handling (it resets to 0.01)
        pass
