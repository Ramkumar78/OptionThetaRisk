import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_turtle_setups
from unittest.mock import patch
import pandas as pd
import numpy as np

scenarios('../features/turtle_strategy.feature')

@pytest.fixture
def mock_market_data_turtle():
    dates = pd.date_range(start="2023-01-01", periods=50, freq="B")
    close = np.full(50, 100.0)
    # Breakout
    close[-1] = 120.0
    df = pd.DataFrame({
        "Open": close, "High": close, "Low": close, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when(parsers.parse('I run the Turtle screener for timeframe "{time_frame}"'), target_fixture="results")
def run_turtle(mock_market_data_turtle, time_frame):
    # Patch fetch_batch_data_safe in common.screener_utils because ScreeningRunner uses it
    with patch('option_auditor.common.screener_utils.fetch_batch_data_safe', return_value=mock_market_data_turtle):
        return screen_turtle_setups(ticker_list=["TURTLE"], time_frame=time_frame)

@then('I should receive a list of results')
def verify_results_list(results):
    assert isinstance(results, list)

@then('I should see a breakout signal')
def verify_basic_turtle_setup_screening(results):
    assert len(results) > 0
    assert "BREAKOUT" in results[0]['signal']

@then(parsers.parse('each result should contain a "{field}" field'))
def verify_field(results, field):
    assert len(results) > 0
    assert field in results[0]
