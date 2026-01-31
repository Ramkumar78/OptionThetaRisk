import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_bull_put_spreads
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

scenarios('../features/bull_put_strategy.feature')

@pytest.fixture
def mock_option_chain():
    """Mock option chain data"""
    puts = pd.DataFrame({
        'strike': [90, 95, 100, 105, 110],
        'bid': [0.5, 1.0, 1.5, 2.0, 2.5],
        'ask': [0.6, 1.1, 1.6, 2.1, 2.6],
        'lastPrice': [0.55, 1.05, 1.55, 2.05, 2.55],
        'impliedVolatility': [0.2, 0.2, 0.2, 0.2, 0.2]
    })
    chain = MagicMock()
    chain.puts = puts
    return chain

@pytest.fixture
def mock_ticker(mock_option_chain):
    """Mock yf.Ticker"""
    ticker = MagicMock()
    # History
    dates = pd.date_range(end=datetime.now(), periods=200, freq="B") # End today
    close = np.linspace(100, 120, 200) # Uptrend
    hist = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 2000000
    }, index=dates)
    ticker.history.return_value = hist

    # Options: Future dates
    future_date = datetime.now() + timedelta(days=45)
    future_date_str = future_date.strftime("%Y-%m-%d")

    ticker.options = [future_date_str]
    # Chain
    ticker.option_chain.return_value = mock_option_chain
    return ticker

@when('I run the Bull Put screener', target_fixture="results")
def run_bull_put(mock_ticker):
    with patch('option_auditor.strategies.bull_put.yf.Ticker') as mock_ticker_cls:
        mock_ticker_cls.return_value = mock_ticker
        return screen_bull_put_spreads(ticker_list=["TEST"], check_mode=True)

@then('I should receive a list of results')
def verify_results_list(results):
    assert isinstance(results, list)

@then(parsers.parse('each result should contain a "{field}" field'))
def verify_field(results, field):
    assert len(results) > 0
    assert field in results[0]
