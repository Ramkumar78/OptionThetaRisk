import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_bull_put_spreads
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/bull_put_strategy.feature')

@when('I run the Bull Put screener', target_fixture="results")
def run_bull_put_screener(ticker_list):
    # We need to mock yfinance Ticker heavily here
    with patch('option_auditor.screener.yf.Ticker') as mock_ticker_cls:
        mock_ticker = MagicMock()
        mock_ticker_cls.return_value = mock_ticker

        # Mock History (1y)
        dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
        close = np.linspace(300, 400, 252) # Bullish Trend
        df = pd.DataFrame({
            "Open": close, "High": close+5, "Low": close-5, "Close": close, "Volume": 2000000
        }, index=dates)
        mock_ticker.history.return_value = df

        # Mock Options Expirations
        # Use relative dates to ensure it works whenever test runs
        from datetime import date, timedelta
        today = date.today()
        valid_exp = (today + timedelta(days=45)).strftime("%Y-%m-%d")
        mock_ticker.options = (valid_exp,)

        # Mock Option Chain
        mock_chain = MagicMock()

        puts_data = {
            "strike": [380.0, 385.0, 390.0, 395.0, 400.0],
            "lastPrice": [2.0, 3.0, 4.0, 5.0, 6.0],
            "bid": [2.0, 3.0, 4.0, 5.0, 6.0],
            "ask": [2.1, 3.1, 4.1, 5.1, 6.1],
            "impliedVolatility": [0.2, 0.2, 0.2, 0.2, 0.2],
            "volume": [100, 100, 100, 100, 100],
            "openInterest": [500, 500, 500, 500, 500]
        }
        mock_chain.puts = pd.DataFrame(puts_data)
        mock_ticker.option_chain.return_value = mock_chain

        return screen_bull_put_spreads(ticker_list=ticker_list, check_mode=True)
