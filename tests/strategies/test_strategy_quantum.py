import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.strategies.quantum import screen_quantum_setups

# Helper to mock market data
@pytest.fixture
def mock_market_data():
    def _gen(days=200, price=100.0):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=days)
        df = pd.DataFrame({
            'Close': [price] * days,
            'High': [price*1.01] * days,
            'Low': [price*0.99] * days,
            'Open': [price] * days,
            'Volume': [1000000] * days
        }, index=dates)
        # Add some variation for calculation
        df['Close'] = df['Close'] + np.random.normal(0, 1, days)
        return df
    return _gen

@patch('option_auditor.strategies.quantum.get_cached_market_data')
@patch('option_auditor.strategies.quantum.generate_human_verdict')
@patch('option_auditor.strategies.quantum.kalman_filter')
@patch('option_auditor.strategies.quantum.shannon_entropy')
@patch('option_auditor.strategies.quantum.calculate_hurst')
def test_screen_quantum_buy(mock_hurst, mock_entropy, mock_kalman, mock_verdict, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df

    # Mock Physics
    mock_hurst.return_value = 0.65 # Strong Trend
    mock_entropy.return_value = 0.5 # Low entropy
    mock_kalman.return_value = pd.Series(np.linspace(90, 100, 250), index=df.index) # Up slope
    mock_verdict.return_value = ("BUY (Strong Trend)", "Reasoning")

    results = screen_quantum_setups(ticker_list=["QUANT"], region="us")

    assert len(results) == 1
    res = results[0]
    assert res['hurst'] == 0.65
    assert "BUY" in res['human_verdict']
    assert res['verdict_color'] == "green"

@patch('option_auditor.strategies.quantum.get_cached_market_data')
@patch('option_auditor.strategies.quantum.generate_human_verdict')
@patch('option_auditor.strategies.quantum.kalman_filter')
@patch('option_auditor.strategies.quantum.shannon_entropy')
@patch('option_auditor.strategies.quantum.calculate_hurst')
def test_screen_quantum_random_walk(mock_hurst, mock_entropy, mock_kalman, mock_verdict, mock_cache, mock_market_data):
    df = mock_market_data(days=250, price=100.0)
    mock_cache.return_value = df

    mock_hurst.return_value = 0.50 # Random
    mock_entropy.return_value = 0.9 # High entropy
    mock_kalman.return_value = pd.Series([100.0]*250, index=df.index)
    mock_verdict.return_value = ("RANDOM WALK", "Avoid")

    results = screen_quantum_setups(ticker_list=["RND"], region="us")

    assert len(results) == 1
    assert "RANDOM" in results[0]['human_verdict']
    assert results[0]['verdict_color'] == "gray"
    assert results[0]['score'] == 0

@patch('option_auditor.strategies.quantum.get_cached_market_data')
def test_screen_quantum_short_history(mock_cache, mock_market_data):
    df = mock_market_data(days=50) # Too short
    mock_cache.return_value = df

    results = screen_quantum_setups(ticker_list=["SHORT"], region="us")
    assert len(results) == 0

@patch('option_auditor.strategies.quantum.get_cached_market_data', side_effect=Exception("Cache Missing"))
@patch('option_auditor.strategies.quantum.fetch_batch_data_safe')
@patch('option_auditor.strategies.quantum.generate_human_verdict')
@patch('option_auditor.strategies.quantum.kalman_filter')
@patch('option_auditor.strategies.quantum.shannon_entropy')
@patch('option_auditor.strategies.quantum.calculate_hurst')
def test_quantum_fallback_and_nan(mock_hurst, mock_entropy, mock_kalman, mock_verdict, mock_fetch, mock_cache):
    """
    Tests fallback to fetch_batch_data_safe and handling of NaNs.
    Merged from tests/test_quantum_reproduce.py
    """
    # Create mock data with NaNs to test serialization?
    # Actually, we rely on the math functions returning None or valid values.
    # But let's verify logic handles None/NaNs from math utils.
    dates = pd.date_range(start='2023-01-01', periods=250)
    df = pd.DataFrame({
        'Close': np.random.rand(250) * 100,
        'High': np.random.rand(250) * 105,
        'Low': np.random.rand(250) * 95,
        'Open': np.random.rand(250) * 100,
        'Volume': np.random.randint(100, 1000, 250)
    }, index=dates)

    # Mock MultiIndex return for fetch_batch_data_safe
    mock_data = pd.concat([df], keys=['AAPL'], axis=1)
    mock_fetch.return_value = mock_data

    # Mock Math returns as NaN/None
    mock_hurst.return_value = None
    mock_entropy.return_value = None
    mock_kalman.return_value = pd.Series([100]*250)
    mock_verdict.return_value = ("WAIT", "Mock Rationale")

    results = screen_quantum_setups(ticker_list=['AAPL'], region='us')

    # ASSERT FALLBACK HAPPENED
    mock_fetch.assert_called_once()

    assert len(results) == 1
    res = results[0]
    assert res['hurst'] is None
    assert res['entropy'] is None

    # Check JSON serializability
    import json
    try:
        json.dumps(res)
    except ValueError as e:
        pytest.fail(f"JSON Serialization Failed: {e}")
