import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_alpha_101
from unittest.mock import patch
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/alpha101_strategy.feature')

@pytest.fixture
def mock_market_data_alpha():
    """Mock yfinance data for Alpha 101. Requires Close > Open and significant move for alpha > 0.5"""
    dates = pd.date_range(start="2023-01-01", periods=60, freq="B")
    # Base price movement
    close = np.linspace(100, 150, 60)
    open_price = close.copy()

    # Make the last day have a strong alpha
    # Alpha = (Close - Open) / ((High - Low) + 0.001)
    # We want Alpha > 0.5
    # Let High = Close + 1, Low = Open - 1
    # Let Close = Open + 10 (Big Move)
    # Alpha = 10 / ((Close+1 - (Open-1)) + 0.001) = 10 / (12 + 0.001) approx 0.8

    open_price[-1] = 150
    close[-1] = 160
    high = close + 1
    low = open_price - 1

    df = pd.DataFrame({
        "Open": open_price, "High": high, "Low": low, "Close": close, "Volume": 1000000
    }, index=dates)
    return df

@when(parsers.parse('I run the Alpha 101 screener for timeframe "{time_frame}"'), target_fixture="results")
def run_alpha_screener(ticker_list, time_frame, mock_market_data_alpha):
     with patch('option_auditor.screener._prepare_data_for_ticker', return_value=mock_market_data_alpha):
        return screen_alpha_101(ticker_list=ticker_list, time_frame=time_frame)
