import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_alpha_101
from unittest.mock import patch
import pandas as pd
import numpy as np

scenarios('../features/alpha101_strategy.feature')

@pytest.fixture
def mock_market_data_alpha():
    # Increase to 20 periods to satisfy ATR(14)
    dates = pd.date_range(start="2023-01-01", periods=20, freq="B")
    close = np.full(20, 100.0)
    # Spike on last day: Close >> Open
    close[-1] = 105.0
    open_p = np.full(20, 100.0)
    open_p[-1] = 100.0

    df = pd.DataFrame({
        "Open": open_p, "High": close+1, "Low": close-1, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when(parsers.parse('I run the Alpha 101 screener for timeframe "{time_frame}"'), target_fixture="results")
def run_alpha(mock_market_data_alpha, time_frame):
     # Patch BOTH cache and live fetch to ensure data is returned
     with patch('option_auditor.common.screener_utils.fetch_batch_data_safe', return_value=mock_market_data_alpha), \
          patch('option_auditor.common.screener_utils.get_cached_market_data', return_value=mock_market_data_alpha):
         return screen_alpha_101(ticker_list=["ALPHA"], time_frame=time_frame)

@then('I should receive a list of results')
def verify_results_list(results):
    assert isinstance(results, list)

@then('I should see a momentum burst signal')
def verify_alpha_101_setup_screening(results):
    assert len(results) > 0
    assert results[0]['alpha_101'] > 0

@then(parsers.parse('each result should contain a "{field}" field'))
def verify_field(results, field):
    assert len(results) > 0
    assert field in results[0]
