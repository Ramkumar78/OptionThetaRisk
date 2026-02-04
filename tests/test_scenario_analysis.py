import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.portfolio_risk import analyze_scenario

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_call(mock_get_data):
    # Mock Data: NVDA at 100, Flat history (Vol = 0 but default fallback 0.4)
    dates = pd.date_range("2023-01-01", periods=60)
    # Using MultiIndex (Ticker, OHLC)
    tuples = [("NVDA", "Close")]
    index = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame(np.random.randn(60, 1) + 100, index=dates, columns=index)
    # Set last price to exact 100
    df.iloc[-1] = 100.0

    mock_get_data.return_value = df

    # Position: 1 Call, Strike 100, Expiring in 1 year
    expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    positions = [{
        "ticker": "NVDA",
        "type": "call",
        "strike": 100,
        "expiry": expiry,
        "qty": 1
    }]

    # 1. Base Case (No Shock)
    # Note: calculate_option_price might differ slightly due to time decay if we don't mock time,
    # but here start and end time are same "now".
    scenario = {"price_change_pct": 0, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)

    # PnL should be 0 because S_new = S_old
    assert res["pnl"] == 0.0
    assert res["details"][0]["S_old"] == 100.0
    assert res["details"][0]["S_new"] == 100.0

    # 2. Price Shock +10%
    scenario = {"price_change_pct": 10, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)

    # Call Delta is positive, so PnL should be positive
    assert res["pnl"] > 0
    assert res["details"][0]["S_new"] == 110.0
    assert res["details"][0]["val_new"] > res["details"][0]["val_old"]

    # 3. Price Shock -10%
    scenario = {"price_change_pct": -10, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)

    assert res["pnl"] < 0
    assert res["details"][0]["S_new"] == 90.0

    # 4. Vol Shock +50%
    scenario = {"price_change_pct": 0, "vol_change_pct": 50}
    res = analyze_scenario(positions, scenario)

    # Vega is positive, so PnL positive
    assert res["pnl"] > 0
    # Check IV
    old_iv = res["details"][0]["IV_old"]
    new_iv = res["details"][0]["IV_new"]
    # Should be roughly +50%
    assert new_iv > old_iv
    assert np.isclose(new_iv, old_iv * 1.5, atol=1.0) # tolerance for rounding

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_put(mock_get_data):
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=60)
    tuples = [("TSLA", "Close")]
    index = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame(np.full((60, 1), 200.0), index=dates, columns=index)
    mock_get_data.return_value = df

    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    positions = [{
        "ticker": "TSLA",
        "type": "put",
        "strike": 190, # OTM Put
        "expiry": expiry,
        "qty": 1
    }]

    # Price Drop -10% -> Put gains value
    scenario = {"price_change_pct": -10, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)

    assert res["pnl"] > 0
    assert res["details"][0]["S_new"] == 180.0 # 200 * 0.9
