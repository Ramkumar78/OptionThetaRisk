import pytest
from unittest.mock import patch
import pandas as pd
from option_auditor.strategies.hybrid import screen_confluence_scan
from option_auditor.strategies.grandmaster_screener import GrandmasterScreener
from option_auditor.common.signal_type import SignalType

# --- Class Tests ---
class TestGrandmasterStrategy:
    def test_grandmaster_strong_buy(self, mock_market_data):
        # Create data that triggers a strong buy in GrandmasterScreener
        # Logic:
        # 1. Trend OK: Close > SMA200, SMA50 > SMA200, Close > SMA50, Close > Low52*1.25, Close > High52*0.75
        # 2. Breakout: Close > Donchian_High_20
        # 3. Volume: RVol > 1.2

        # We need roughly 260 days to fill moving averages
        days = 300
        df = mock_market_data(days=days, price=100.0, trend="up", volatility=0.01)

        # Ensure trend conditions are met (mock_market_data trend="up" usually creates a nice curve)
        # But we need specific volume spike and breakout

        # Modify the last row to be a breakout
        # First, ensure columns exist (mock_market_data creates Capitalized ones, Screener normalizes)
        # mock_market_data creates: Open, High, Low, Close, Volume

        # Force a trend
        df['Close'] = [100 + i*0.5 for i in range(days)]
        df['High'] = df['Close'] + 1
        df['Low'] = df['Close'] - 1
        df['Open'] = df['Close'] - 0.5
        df['Volume'] = 1000000

        # Last day breakout:
        # Donchian High 20 is max of previous 20 highs.
        # With linear trend, previous high is i-1.
        # So current high > previous high is guaranteed.

        # Volume spike
        df.iloc[-1, df.columns.get_loc('Volume')] = 1500000 # 1.5x average

        screener = GrandmasterScreener()
        result = screener.analyze(df)

        # The logic requires Close > Donchian_High_20 (which is shifted by 1)
        # High[-1] = 100 + 299*0.5 + 1 = 250.5
        # Donchian High is Max(High[-21:-1]) = High[-2] = 250.0
        # Close[-1] = 249.5.
        # Wait, linear trend: Close[-1] = 100 + 299*0.5 = 249.5.
        # High[-2] (Donchian Ref) = 100 + 298*0.5 + 1 = 250.0.
        # So Close[-1] (249.5) < Donchian High (250). No Breakout.

        # Let's force a massive jump at the end
        df.iloc[-1, df.columns.get_loc('Close')] = 300.0
        df.iloc[-1, df.columns.get_loc('High')] = 305.0

        result = screener.analyze(df)

        # Should be BUY BREAKOUT
        assert "BUY BREAKOUT" in result['signal']
        assert result['quality_score'] > 100 # Trend (100) + RVol (1.5 * 10 = 15)

    def test_grandmaster_wait(self, mock_market_data):
        df = mock_market_data(days=300, price=100.0, trend="flat")
        screener = GrandmasterScreener()
        result = screener.analyze(df)
        assert result['signal'] == "WAIT" or result['signal'] == "WATCHLIST"

# --- Functional Tests ---

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.StrategyAnalyzer')
def test_screen_confluence_strong_buy(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    # Mock Analyzer Instance
    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "BULLISH" # Score +1
    mock_instance.check_fourier.return_value = ("BOTTOM", -0.9) # Score +2
    mock_instance.check_momentum.return_value = "NEUTRAL"

    # Total Score 3 -> STRONG BUY

    results = screen_confluence_scan(ticker_list=["MASTER"], check_mode=True)

    assert len(results) == 1
    res = results[0]
    assert res['confluence_score'] == 3
    assert "STRONG BUY" in res['verdict']

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.StrategyAnalyzer')
def test_screen_confluence_sell(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "BEARISH"
    mock_instance.check_fourier.return_value = ("TOP", 0.9)
    mock_instance.check_momentum.return_value = "OVERBOUGHT"

    # ISA Bearish + Top = Strong Sell logic in function

    results = screen_confluence_scan(ticker_list=["SELL"], check_mode=True)

    assert len(results) == 1
    assert "STRONG SELL" in results[0]['verdict']

@patch('option_auditor.strategies.hybrid.fetch_batch_data_safe')
@patch('option_auditor.strategies.hybrid.get_cached_market_data')
@patch('option_auditor.strategies.hybrid.StrategyAnalyzer')
def test_screen_confluence_wait(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "NEUTRAL"
    mock_instance.check_fourier.return_value = ("MID", 0.0)
    mock_instance.check_momentum.return_value = "NEUTRAL"

    results = screen_confluence_scan(ticker_list=["WAIT"], check_mode=True)

    # Wait results are still returned, just with low score
    assert len(results) == 1
    assert results[0]['confluence_score'] == 0
    assert results[0]['verdict'] == "WAIT"
