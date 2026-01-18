import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_turtle_setups
from unittest.mock import patch
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/turtle_strategy.feature')

@pytest.fixture
def mock_market_data_turtle():
    """Mock yfinance data for Turtle (requires highs for breakout)"""
    dates = pd.date_range(start="2023-01-01", periods=60, freq="B")
    close = np.linspace(100, 150, 60)
    # Make the last price a 20-day high
    close[-1] = 160
    df = pd.DataFrame({
        "Open": close, "High": close * 1.05, "Low": close * 0.95, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when(parsers.parse('I run the Turtle screener for timeframe "{time_frame}"'), target_fixture="results")
def run_turtle_screener(ticker_list, time_frame, mock_market_data_turtle):
    with patch('option_auditor.screener._prepare_data_for_ticker', return_value=mock_market_data_turtle):
        return screen_turtle_setups(ticker_list=ticker_list, time_frame=time_frame)
