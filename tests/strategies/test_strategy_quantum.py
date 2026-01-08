import pytest
from unittest.mock import patch
import pandas as pd
from option_auditor.screener import screen_quantum_setups

@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener.QuantPhysicsEngine')
def test_screen_quantum_buy(mock_engine, mock_cache, mock_market_data):
    df = mock_market_data(days=150, price=100.0)

    mock_cache.return_value = df

    # Mock Physics Engine
    mock_engine.calculate_hurst.return_value = 0.65 # Strong Trend
    mock_engine.shannon_entropy.return_value = 2.0 # Low entropy
    mock_engine.kalman_filter.return_value = pd.Series([99.0, 100.0], index=df.index[-2:]) # Up slope
    mock_engine.generate_human_verdict.return_value = ("BUY (Strong Trend)", "Reasoning")

    results = screen_quantum_setups(ticker_list=["QUANT"], region="us")

    assert len(results) == 1
    res = results[0]
    assert res['hurst'] == 0.65
    assert "BUY" in res['human_verdict']
    assert res['verdict_color'] == "green"

@patch('option_auditor.screener.get_cached_market_data')
@patch('option_auditor.screener.QuantPhysicsEngine')
def test_screen_quantum_random_walk(mock_engine, mock_cache, mock_market_data):
    df = mock_market_data(days=150, price=100.0)
    mock_cache.return_value = df

    mock_engine.calculate_hurst.return_value = 0.50 # Random
    mock_engine.shannon_entropy.return_value = 4.0 # High entropy
    mock_engine.kalman_filter.return_value = pd.Series([100.0, 100.0], index=df.index[-2:])
    mock_engine.generate_human_verdict.return_value = ("RANDOM WALK", "Avoid")

    results = screen_quantum_setups(ticker_list=["RND"], region="us")

    assert len(results) == 1
    assert "RANDOM" in results[0]['human_verdict']
    assert results[0]['verdict_color'] == "gray"
    assert results[0]['score'] == 0

@patch('option_auditor.screener.get_cached_market_data')
def test_screen_quantum_short_history(mock_cache, mock_market_data):
    df = mock_market_data(days=50) # Too short for Hurst
    mock_cache.return_value = df

    results = screen_quantum_setups(ticker_list=["SHORT"], region="us")
    assert len(results) == 0
