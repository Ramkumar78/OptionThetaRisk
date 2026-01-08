import pytest
from unittest.mock import patch
import pandas as pd
from option_auditor.screener import screen_master_convergence
from option_auditor.strategies.grandmaster import GrandmasterStrategy

# --- Class Tests ---
class TestGrandmasterStrategy:
    def test_grandmaster_strong_buy(self, mock_market_data):
        df = mock_market_data(days=250, price=100.0, trend="up")
        pass

# --- Functional Tests ---

@patch('option_auditor.screener.fetch_batch_data_safe')
@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener.StrategyAnalyzer')
def test_screen_master_strong_buy(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    # Mock Analyzer Instance
    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "BULLISH" # Score +1
    mock_instance.check_fourier.return_value = ("BOTTOM", -0.9) # Score +2
    mock_instance.check_momentum.return_value = "NEUTRAL"

    # Total Score 3 -> STRONG BUY

    results = screen_master_convergence(ticker_list=["MASTER"], check_mode=True)

    assert len(results) == 1
    res = results[0]
    assert res['confluence_score'] == 3
    assert "STRONG BUY" in res['verdict']

@patch('option_auditor.screener.fetch_batch_data_safe')
@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener.StrategyAnalyzer')
def test_screen_master_sell(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "BEARISH"
    mock_instance.check_fourier.return_value = ("TOP", 0.9)
    mock_instance.check_momentum.return_value = "OVERBOUGHT"

    # ISA Bearish + Top = Strong Sell logic in function

    results = screen_master_convergence(ticker_list=["SELL"], check_mode=True)

    assert len(results) == 1
    assert "STRONG SELL" in results[0]['verdict']

@patch('option_auditor.screener.fetch_batch_data_safe')
@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener.StrategyAnalyzer')
def test_screen_master_wait(mock_analyzer_cls, mock_cache, mock_fetch, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df
    mock_fetch.return_value = df

    mock_instance = mock_analyzer_cls.return_value
    mock_instance.check_isa_trend.return_value = "NEUTRAL"
    mock_instance.check_fourier.return_value = ("MID", 0.0)
    mock_instance.check_momentum.return_value = "NEUTRAL"

    results = screen_master_convergence(ticker_list=["WAIT"], check_mode=True)

    # Wait results are still returned, just with low score
    assert len(results) == 1
    assert results[0]['confluence_score'] == 0
    assert results[0]['verdict'] == "WAIT"
