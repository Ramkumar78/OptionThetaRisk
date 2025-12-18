import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import pybreaker
from option_auditor.common.resilience import data_api_breaker, ResiliencyGuru
from option_auditor.common.data_utils import fetch_batch_data_safe, fetch_data_with_retry
from option_auditor.strategies.base import BaseStrategy

# Reset breaker state before tests
@pytest.fixture(autouse=True)
def reset_breaker():
    data_api_breaker.close()
    yield
    data_api_breaker.close()

def test_circuit_breaker_activates_on_failure():
    """Verify that the circuit breaker opens after consecutive failures."""

    # Configure breaker to fail fast for test
    # We can't easily reconfigure the global breaker, so we just simulate calls.
    # The breaker in data_utils is imported.

    # Mock yfinance to raise Exception
    with patch('yfinance.download', side_effect=Exception("API Down")):
        # We need to call enough times to trip the breaker.
        # fail_max is 3 in resilience.py

        # Call 1
        res = fetch_batch_data_safe(["AAPL"])
        assert res.empty

        # Call 2
        res = fetch_batch_data_safe(["AAPL"])
        assert res.empty

        # Call 3
        res = fetch_batch_data_safe(["AAPL"])
        assert res.empty

        # Now breaker should be OPEN
        assert data_api_breaker.current_state == 'open'

        # Next call should not even try yfinance (would raise side_effect if called)
        # But we patch it anyway. If breaker works, it won't call the mock function body
        # or it will raise CircuitBreakerError which fetch_batch catches.

        res = fetch_batch_data_safe(["AAPL"])
        assert res.empty

def test_resiliency_guru_fallback():
    """Test the fallback mechanism."""
    # This is a bit manual since SCREENER_CACHE is global
    from option_auditor.common.constants import SCREENER_CACHE
    SCREENER_CACHE["last_good_scan"] = {"test": "data"}

    assert ResiliencyGuru.fallback_fetch() == {"test": "data"}

def test_strategy_market_volatility_check():
    """Test the volatility circuit breaker in BaseStrategy."""

    class ConcreteStrategy(BaseStrategy):
        def analyze(self, df):
            return {}

    strategy = ConcreteStrategy()

    # Case 1: Normal Volatility
    df_normal = pd.DataFrame({
        'ATR': [1.0, 1.1, 1.0, 0.9, 1.0]
    })
    assert strategy.check_market_volatility(df_normal) is None

    # Case 2: Extreme Volatility (Last ATR 5x mean)
    # Mean of [1, 1, 1, 1] is 1. If next is 6, mean becomes (10/5)=2. 6 > 2*5 (10)? No.
    # We need current > mean * 5.
    # If history is [1, 1, 1, 1], mean is 1. New value 6. Mean becomes ~2.
    # Wait, check logic: `current_atr > (mean_atr * 5)`
    # The mean includes the current value if we pass the whole DF and call .mean().

    df_high_vol = pd.DataFrame({
        'ATR': [1.0] * 10 + [10.0]
    })
    # Mean is approx (10 + 10) / 11 = 1.81.
    # Current is 10.
    # 1.81 * 5 = 9.05.
    # 10 > 9.05 -> TRIPPED.

    assert strategy.check_market_volatility(df_high_vol) == "TRIPPED: HIGH VOLATILITY"

def test_breaker_status_endpoint():
    """Test that the app exposes breaker status."""
    from webapp.app import app
    client = app.test_client()

    # Ensure closed initially
    data_api_breaker.close()

    resp = client.get('/api/screener/status')
    assert resp.status_code == 200
    assert resp.json['api_health'] == 'closed'
    assert resp.json['is_fallback'] is False

    # Trip it
    data_api_breaker.open()
    resp = client.get('/api/screener/status')
    assert resp.json['api_health'] == 'open'
    assert resp.json['is_fallback'] is True
