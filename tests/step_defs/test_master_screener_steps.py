import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_master_convergence
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

scenarios('../features/master_screener.feature')

@pytest.fixture
def mock_market_data_master():
    dates = pd.date_range(start="2023-01-01", periods=250, freq="B")
    close = np.linspace(100, 150, 250)
    df = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when('I run the Master Convergence screener', target_fixture="results")
def run_master_screener(mock_market_data_master):
    # Mock data fetch
    big_data = pd.concat({"TEST": mock_market_data_master}, axis=1)

    with patch('option_auditor.strategies.hybrid.get_cached_market_data', return_value=big_data), \
         patch('option_auditor.strategies.hybrid.fetch_batch_data_safe', return_value=big_data):
        return screen_master_convergence(ticker_list=["TEST"], check_mode=True)

@then('I should receive a list of results')
def verify_results_list(results):
    assert isinstance(results, list)

@then('each result should contain a "confluence_score" field')
def verify_confluence_field(results):
    assert len(results) > 0
    assert 'confluence_score' in results[0]

@then(parsers.parse('the result should indicate "{trend}" trend if price is above SMA200'))
def verify_trend(results, trend):
    # Our mock data is uptrend (100 -> 150), so it should be BULLISH
    assert len(results) > 0
    # In logic: if isa_trend == "BULLISH"
    assert results[0]['isa_trend'] == trend
