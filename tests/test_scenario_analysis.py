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
    scenario = {"price_change_pct": 0, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)
    assert res["pnl"] == 0.0
    assert res["details"][0]["S_old"] == 100.0
    assert res["details"][0]["S_new"] == 100.0

    # 2. Price Shock +10%
    scenario = {"price_change_pct": 10, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)
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
    assert res["pnl"] > 0
    old_iv = res["details"][0]["IV_old"]
    new_iv = res["details"][0]["IV_new"]
    assert new_iv > old_iv
    assert np.isclose(new_iv, old_iv * 1.5, atol=1.0)

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_put(mock_get_data):
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
    assert res["details"][0]["S_new"] == 180.0

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_mixed_portfolio(mock_get_data):
    # Mock Data: NVDA at 100, TSLA at 200
    dates = pd.date_range("2023-01-01", periods=60)
    data = {
        ("NVDA", "Close"): np.full(60, 100.0),
        ("TSLA", "Close"): np.full(60, 200.0)
    }
    df = pd.DataFrame(data, index=dates)
    mock_get_data.return_value = df

    expiry = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    positions = [
        {"ticker": "NVDA", "type": "call", "strike": 100, "expiry": expiry, "qty": 1}, # Bullish
        {"ticker": "TSLA", "type": "put", "strike": 200, "expiry": expiry, "qty": 1}  # Bearish
    ]

    # Scenario: Market up 10%
    # NVDA Call gains, TSLA Put loses
    scenario = {"price_change_pct": 10, "vol_change_pct": 0}
    res = analyze_scenario(positions, scenario)

    details = {d['ticker']: d for d in res['details']}
    assert details['NVDA']['pnl'] > 0
    assert details['TSLA']['pnl'] < 0

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_combined_shock(mock_get_data):
    dates = pd.date_range("2023-01-01", periods=60)
    tuples = [("SPY", "Close")]
    index = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame(np.full((60, 1), 400.0), index=dates, columns=index)
    mock_get_data.return_value = df

    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    # ATM Put
    positions = [{
        "ticker": "SPY",
        "type": "put",
        "strike": 400,
        "expiry": expiry,
        "qty": 1
    }]

    # Scenario: Crash (-10% price, +50% vol)
    # Put should gain massively from both delta (price drop) and vega (vol up)
    scenario = {"price_change_pct": -10, "vol_change_pct": 50}
    res = analyze_scenario(positions, scenario)

    assert res['pnl'] > 0
    d = res['details'][0]
    assert d['S_new'] == 360.0
    assert d['IV_new'] > d['IV_old']

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_missing_data(mock_get_data):
    # Mock empty data
    mock_get_data.return_value = pd.DataFrame()

    expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    positions = [{
        "ticker": "UNKNOWN",
        "type": "call",
        "strike": 100,
        "expiry": expiry,
        "qty": 1
    }]

    scenario = {"price_change_pct": 10}
    # Should not crash, but return 0 PnL because price is 0
    res = analyze_scenario(positions, scenario)

    # Logic in analyze_scenario skips positions where S <= 0 or can't be fetched
    # If fetch fails, S=0. "if S <= 0: continue".
    # So details should be empty? Or contained error?
    # Logic: "if S <= 0: continue" inside the loop.
    # So details will be empty.

    assert res['pnl'] == 0.0
    assert len(res['details']) == 0

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_invalid_input(mock_get_data):
    mock_get_data.return_value = pd.DataFrame()

    # Missing keys
    positions = [{"ticker": "AAPL"}] # Missing type, strike, expiry, qty
    scenario = {"price_change_pct": 10}

    res = analyze_scenario(positions, scenario)
    # Should handle gracefully
    assert res['pnl'] == 0.0

@patch("option_auditor.portfolio_risk.get_cached_market_data")
def test_analyze_scenario_edge_cases(mock_get_data):
    dates = pd.date_range("2023-01-01", periods=60)
    tuples = [("AAPL", "Close")]
    index = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame(np.full((60, 1), 150.0), index=dates, columns=index)
    mock_get_data.return_value = df

    # Expired Option
    expiry = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    positions = [{
        "ticker": "AAPL",
        "type": "call",
        "strike": 150,
        "expiry": expiry,
        "qty": 1
    }]

    scenario = {"price_change_pct": 10}
    res = analyze_scenario(positions, scenario)

    # Expired option value should be intrinsic (if ITM) or 0?
    # Logic: T < 0 -> T = 0.
    # If T=0, BS model gives intrinsic value.
    # S=150, Strike=150 -> Intrinsic=0.
    # S_new=165, Strike=150 -> Intrinsic=15.
    # PnL = 15.

    assert res['pnl'] > 0

    # Verify Extreme Volatility
    # Vol shock -100% (impossible, min capped at 0.01)
    scenario_vol = {"vol_change_pct": -200}
    res_vol = analyze_scenario(positions, scenario_vol)
    # IV should be floored
    assert res_vol['details'][0]['IV_new'] >= 1.0 # 0.01 * 100
