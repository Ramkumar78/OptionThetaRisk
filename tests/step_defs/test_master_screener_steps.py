import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from option_auditor.screener import screen_master_convergence
from unittest.mock import patch
import pandas as pd
import numpy as np

# Load scenarios from the feature file
scenarios('../features/master_screener.feature')

@when('I run the Master Convergence screener', target_fixture="results")
def run_master_screener(ticker_list):
    # Mock data with 250 days (enough for 200 SMA)
    dates = pd.date_range(start="2023-01-01", periods=250, freq="B")

    # Generate prices such that Current Price (200) > SMA 200 (~150).
    close = np.linspace(100, 200, 250)

    df = pd.DataFrame({
        "Open": close, "High": close+1, "Low": close-1, "Close": close, "Volume": 1000000
    }, index=dates)

    # We need to construct the MultiIndex DataFrame as expected by the screener
    dfs = [df for _ in ticker_list]
    big_data = pd.concat(dfs, axis=1, keys=ticker_list)

    # Patch BOTH get_cached_market_data AND fetch_batch_data_safe
    # because check_mode=True triggers fetch_batch_data_safe
    with patch('option_auditor.screener.get_cached_market_data', return_value=big_data), \
         patch('option_auditor.screener.fetch_batch_data_safe', return_value=big_data):

        return screen_master_convergence(ticker_list=ticker_list, check_mode=True)

@then('the result should indicate "BULLISH" trend if price is above SMA200')
def check_bullish_trend(results):
    for res in results:
        # Debug print if fails
        if res["isa_trend"] != "BULLISH":
             print(f"FAILED: {res['ticker']} Trend: {res['isa_trend']}")
        assert res["isa_trend"] == "BULLISH"
