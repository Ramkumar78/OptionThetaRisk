import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_quantum_setups
from unittest.mock import patch
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/quantum_strategy.feature')

@when('I run the Quantum screener', target_fixture="results")
def run_quantum_screener(ticker_list):
    # Mock data with enough history for Hurst (120 days min)
    dates = pd.date_range(start="2023-01-01", periods=200, freq="B")

    # Generate Trending data (Hurst > 0.5)
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 200) # Positive mean return
    price_path = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        "Open": price_path, "High": price_path*1.01, "Low": price_path*0.99, "Close": price_path, "Volume": 1000000
    }, index=dates)

    # Quantum screener logic handles MultiIndex or Flat.
    # It calls get_cached_market_data.

    with patch('option_auditor.common.screener_utils.get_cached_market_data') as mock_data, \
         patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_fetch:

        # Construct MultiIndex DF to be safe
        dfs = [df for _ in ticker_list]
        big_data = pd.concat(dfs, axis=1, keys=ticker_list)

        # Mock both to be sure
        mock_data.return_value = big_data
        mock_fetch.return_value = big_data

        return screen_quantum_setups(ticker_list=ticker_list)
