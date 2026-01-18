import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_5_13_setups
from unittest.mock import patch
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/screener.feature')

@pytest.fixture
def mock_market_data():
    """Mock yfinance data"""
    dates = pd.date_range(start="2023-01-01", periods=50, freq="B")
    close = np.linspace(100, 150, 50)
    df = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when(parsers.parse('I run the 5/13 screener for timeframe "{time_frame}"'), target_fixture="results")
def run_screener(ticker_list, time_frame, mock_market_data):
    with patch('option_auditor.screener._prepare_data_for_ticker', return_value=mock_market_data):
        return screen_5_13_setups(ticker_list=ticker_list, time_frame=time_frame)
