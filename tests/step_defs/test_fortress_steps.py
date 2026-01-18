import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_dynamic_volatility_fortress
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/fortress_strategy.feature')

@when('I run the Fortress screener', target_fixture="results")
def run_fortress_screener(ticker_list):
    # Mock data
    dates = pd.date_range(start="2023-01-01", periods=200, freq="B")
    close = np.linspace(300, 400, 200) # Uptrend

    df = pd.DataFrame({
        "Open": close, "High": close+5, "Low": close-5, "Close": close, "Volume": 5000000
    }, index=dates)

    # Patch the location where the function imports it from (inside the function)
    # Since it does 'from option_auditor.common.data_utils import get_cached_market_data'
    # We must patch 'option_auditor.common.data_utils.get_cached_market_data'

    with patch('option_auditor.common.data_utils.get_cached_market_data') as mock_data, \
         patch('option_auditor.screener._get_market_regime') as mock_vix, \
         patch('option_auditor.screener._calculate_trend_breakout_date', return_value="2023-01-01"):

        # Mock VIX
        mock_vix.return_value = 15.0

        # Mock Stock Data - MultiIndex to be safe
        mi_columns = pd.MultiIndex.from_product([ticker_list, df.columns])
        # Replicate data for each ticker (correct construction)
        data_dict = {}
        for t in ticker_list:
            for col in df.columns:
                data_dict[(t, col)] = df[col]

        big_data = pd.DataFrame(data_dict, index=df.index)
        big_data.columns = mi_columns

        mock_data.return_value = big_data

        return screen_dynamic_volatility_fortress(ticker_list=ticker_list)
