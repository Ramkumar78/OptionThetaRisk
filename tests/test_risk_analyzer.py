import pytest
import pandas as pd
import numpy as np
from option_auditor.models import TradeGroup, StressTestResult
from option_auditor.risk_analyzer import calculate_black_swan_impact

@pytest.fixture
def mock_prices():
    return {
        "AAPL": 150.0,
        "TSLA": 200.0,
        "SPY": 400.0
    }

@pytest.fixture
def sample_trade_groups():
    now = pd.Timestamp.now()
    expiry_30d = now + pd.Timedelta(days=30)

    # 1. Long Stock (AAPL)
    g1 = TradeGroup(
        contract_id="1", symbol="AAPL", expiry=None, strike=None, right=None,
        qty_net=10, pnl=0, fees=0
    )

    # 2. Long Call Option (TSLA)
    # Strike 200 (ATM), 30 DTE
    g2 = TradeGroup(
        contract_id="2", symbol="TSLA", expiry=expiry_30d, strike=200.0, right='C',
        qty_net=1, pnl=0, fees=0
    )

    # 3. Short Put Option (SPY)
    # Strike 380 (OTM), 30 DTE
    g3 = TradeGroup(
        contract_id="3", symbol="SPY", expiry=expiry_30d, strike=380.0, right='P',
        qty_net=-1, pnl=0, fees=0
    )

    return [g1, g2, g3]

def test_black_swan_impact_scenarios(sample_trade_groups, mock_prices):
    results = calculate_black_swan_impact(sample_trade_groups, mock_prices)

    # Check we have 6 scenarios
    assert len(results) == 6
    scenarios = [r.scenario_name for r in results]
    expected_scenarios = [
        "Market -20%", "Market -10%", "Market -5%",
        "Market +5%", "Market +10%", "Market +20%"
    ]
    assert scenarios == expected_scenarios

def test_black_swan_impact_values(sample_trade_groups, mock_prices):
    # Focus on "Market +10%"
    # AAPL: 150 -> 165 (+15). Qty 10 -> Gain 150.
    # TSLA: 200 -> 220. Call(200) gains value.
    # SPY: 400 -> 440. Put(380) loses value (becomes less valuable, but since short, we gain).
    # Wait, Put Value decreases -> Short Position Gains (Liab decreases).

    results = calculate_black_swan_impact(sample_trade_groups, mock_prices)
    res_plus_10 = next(r for r in results if r.scenario_name == "Market +10%")

    assert res_plus_10.market_move_pct == 10.0
    # AAPL Gain: 150
    # TSLA Call Gain: Should be positive (Delta ~0.5 -> ~0.6)
    # SPY Put Gain: Short Put, price drops, so we make money.

    assert res_plus_10.portfolio_value_change > 150.0

    # Focus on "Market -10%"
    # AAPL: 150 -> 135 (-15). Qty 10 -> Loss 150.
    # TSLA: 200 -> 180. Call loses value.
    # SPY: 400 -> 360. Put gains value. Short Put -> We lose money.

    res_minus_10 = next(r for r in results if r.scenario_name == "Market -10%")
    assert res_minus_10.market_move_pct == -10.0

    # AAPL Loss: -150
    # TSLA Call Loss: Max loss is limited to premium, but here we calc theoretical price change.
    # SPY Put Loss: Price increases, so liability increases -> Loss.

    assert res_minus_10.portfolio_value_change < -150.0

def test_missing_prices(sample_trade_groups):
    # Only provide price for AAPL
    prices = {"AAPL": 150.0}

    results = calculate_black_swan_impact(sample_trade_groups, prices)
    res_plus_10 = next(r for r in results if r.scenario_name == "Market +10%")

    # Only AAPL should contribute
    # AAPL Gain: 150
    # Others ignored
    assert pytest.approx(res_plus_10.portfolio_value_change, 0.1) == 150.0

def test_empty_portfolio(mock_prices):
    results = calculate_black_swan_impact([], mock_prices)
    assert len(results) == 6
    for r in results:
        assert r.portfolio_value_change == 0.0
        assert r.portfolio_value_change_pct == 0.0

def test_invalid_expiry(mock_prices):
    # TSLA option with invalid expiry
    g = TradeGroup(
        contract_id="2", symbol="TSLA", expiry="INVALID", strike=200.0, right='C',
        qty_net=1
    )

    # Function should handle it gracefully (T=0 -> Intrinsic Value)
    results = calculate_black_swan_impact([g], mock_prices)

    # Market +10% -> TSLA 220. Strike 200. Intrinsic = 20.
    # Market 0% -> TSLA 200. Strike 200. Intrinsic = 0.
    # PnL = 20 * 100 * 1 = 2000.

    res_plus_10 = next(r for r in results if r.scenario_name == "Market +10%")
    # Check if close to 2000
    assert pytest.approx(res_plus_10.portfolio_value_change, 0.1) == 2000.0
