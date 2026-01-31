import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.strategies.fortress import screen_dynamic_volatility_fortress
from unittest.mock import patch
import pandas as pd
import numpy as np

scenarios('../features/fortress_strategy.feature')

@pytest.fixture
def mock_market_data_fortress():
    dates = pd.date_range(start="2023-01-01", periods=200, freq="B")
    close = np.linspace(100, 150, 200)
    # Increase range to ensure ATR% > 2.0 (Vol > 2%)
    # 1.03 / 0.97 => 6% range approx
    df = pd.DataFrame({
        "Open": close, "High": close * 1.03, "Low": close * 0.97, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when('I run the Fortress screener', target_fixture="results")
def run_fortress(mock_market_data_fortress):
    big_data = pd.concat({"FORT": mock_market_data_fortress}, axis=1)

    with patch('option_auditor.strategies.fortress.get_cached_market_data', return_value=big_data), \
         patch('option_auditor.strategies.fortress._get_market_regime') as mock_vix, \
         patch('option_auditor.strategies.fortress._calculate_trend_breakout_date', return_value="2023-01-01"):
        mock_vix.return_value = 15.0 # Low VIX
        return screen_dynamic_volatility_fortress(ticker_list=["FORT"])

@then('I should receive a list of results')
def verify_results_list(results):
    assert isinstance(results, list)

@then('I should see a safe floor calculation')
def verify_fortress_setup_identification(results):
    assert len(results) > 0
    assert 'safety_mult' in results[0]

@then(parsers.parse('each result should contain a "{field}" field'))
def verify_field(results, field):
    assert len(results) > 0
    assert field in results[0]
