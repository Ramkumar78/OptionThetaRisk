import pytest
import pandas as pd
import numpy as np
from option_auditor.models import TradeGroup, StressTestResult
from option_auditor.risk_analyzer import (
    calculate_black_swan_impact,
    check_itm_risk,
    calculate_discipline_score,
    calculate_kelly_criterion
)

@pytest.fixture
def mock_prices():
    return {
        "AAPL": 150.0,
        "TSLA": 200.0,
        "SPY": 400.0,
        "XYZ": 90.0,
        "ABC": 110.0
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

# --- New Tests ---

def test_black_swan_impact_mixed_portfolio(mock_prices):
    # Explicitly test mixed portfolio logic
    # Stock: AAPL 100 shares @ 150. Value = 15000.
    stock_group = TradeGroup(
        contract_id="S1", symbol="AAPL", expiry=None, strike=None, right=None,
        qty_net=100
    )

    # Option: AAPL Call Strike 150 (ATM). 1 Contract.
    # Use expiry 30 days out.
    expiry = pd.Timestamp.now() + pd.Timedelta(days=30)
    option_group = TradeGroup(
        contract_id="O1", symbol="AAPL", expiry=expiry, strike=150.0, right='C',
        qty_net=1
    )

    # Portfolio
    groups = [stock_group, option_group]

    results = calculate_black_swan_impact(groups, mock_prices)

    # Market +10% Scenario
    res_plus_10 = next(r for r in results if r.scenario_name == "Market +10%")

    # Expected Stock Gain: 100 * (150 * 0.10) = 1500.
    expected_stock_gain = 1500.0

    # Expected Option Gain: Call delta ~0.5. Change in underlying = 15.
    # Option Price change approx 0.5 * 15 = 7.5 per share * 100 = 750.
    # Total Gain approx 2250.

    assert res_plus_10.portfolio_value_change > expected_stock_gain
    # Option delta increases but < 1. Max additional gain roughly < 1500.
    assert res_plus_10.portfolio_value_change < (expected_stock_gain + 2000)

    # Market -10% Scenario
    res_minus_10 = next(r for r in results if r.scenario_name == "Market -10%")

    # Expected Stock Loss: -1500.
    # Expected Option Loss: Delta ~0.5. Loss approx -750.
    # Total Loss approx -2250.

    assert res_minus_10.portfolio_value_change < -1500.0
    assert res_minus_10.portfolio_value_change > -3000.0

def test_check_itm_risk_short_put_itm():
    # Short Put ITM: Strike 100, Price 90. Value = Max(0, 100-90) = 10. Liability = -10 * 100 * 1 = -1000.
    # Threshold is -500. Should trigger risk.
    g = TradeGroup(
        contract_id="1", symbol="XYZ", expiry=None, strike=100.0, right='P',
        qty_net=-1 # Short 1 Put
    )
    prices = {"XYZ": 90.0}
    risky, total_exposure, details = check_itm_risk([g], prices)
    assert risky is True
    assert total_exposure == 1000.0
    assert len(details) == 1
    assert "XYZ" in details[0]

def test_check_itm_risk_short_call_itm():
    # Short Call ITM: Strike 100, Price 110. Value = Max(0, 110-100) = 10. Liability = -10 * 100 * 1 = -1000.
    g = TradeGroup(
        contract_id="1", symbol="ABC", expiry=None, strike=100.0, right='C',
        qty_net=-1
    )
    prices = {"ABC": 110.0}
    risky, total_exposure, details = check_itm_risk([g], prices)
    assert risky is True
    assert total_exposure == 1000.0

def test_check_itm_risk_safe():
    # Short Put OTM: Strike 80, Price 90. Value = 0.
    g = TradeGroup(
        contract_id="1", symbol="XYZ", expiry=None, strike=80.0, right='P',
        qty_net=-1
    )
    prices = {"XYZ": 90.0}
    risky, total_exposure, details = check_itm_risk([g], prices)
    assert risky is False
    assert total_exposure == 0.0

def test_check_itm_risk_covered_call():
    # Long Stock 100, Short Call 1 Strike 100. Price 110.
    # Stock Value = 100 * 110 = 11000.
    # Call Liability = (110 - 100) * 100 * -1 = -1000.
    # Net Intrinsic = 11000 - 1000 = 10000 > -500. Safe.

    g_stock = TradeGroup(
        contract_id="1", symbol="ABC", expiry=None, strike=None, right=None,
        qty_net=100 # 100 shares
    )
    g_call = TradeGroup(
        contract_id="2", symbol="ABC", expiry=None, strike=100.0, right='C',
        qty_net=-1 # Short 1 Call
    )

    prices = {"ABC": 110.0}
    risky, total_exposure, details = check_itm_risk([g_stock, g_call], prices)
    assert risky is False

class MockStrategy:
    def __init__(self, name="Strat", pnl=0.0, is_revenge=False, hold_days=1.0, exit_ts=None):
        self.strategy_name = name
        self.net_pnl = pnl
        self.is_revenge = is_revenge
        self._hold_days = hold_days
        self.exit_ts = exit_ts

    def hold_days(self):
        return self._hold_days

def test_calculate_discipline_score():
    # 1. Revenge Trading
    s1 = MockStrategy(is_revenge=True)
    score, details = calculate_discipline_score([s1], [])
    assert score == 90 # 100 - 10
    assert "Revenge Trading" in details[0]

    # 2. Early Cuts Bonus
    # s1 hold=10, s_short_loss hold=1. Avg = 5.5. 0.5 * 5.5 = 2.75. s_short_loss(1) < 2.75.
    # Use different names to avoid Patience Bonus (which compares against own-strategy average)
    s_long = MockStrategy(name="StratA", hold_days=10.0, pnl=100)
    s_short_loss = MockStrategy(name="StratB", pnl=-100, hold_days=1.0)

    # We add a revenge trade to lower score so we can see the bonus effect
    s_revenge = MockStrategy(name="StratC", is_revenge=True, hold_days=10) # -10

    # Strategies: long(10), short_loss(1), revenge(10). Avg hold = 7. Cutoff = 3.5. short_loss(1) qualifies.
    # Score = 100 - 10 (revenge) + 2 (early cut) = 92.

    score, details = calculate_discipline_score([s_long, s_short_loss, s_revenge], [])
    assert score == 92
    assert any("Cutting Losses Early" in d for d in details)

    # 3. Tilt (Rapid Losses)
    now = pd.Timestamp.now()
    loss1 = MockStrategy(pnl=-100, exit_ts=now - pd.Timedelta(hours=1))
    loss2 = MockStrategy(pnl=-100, exit_ts=now - pd.Timedelta(hours=2))
    loss3 = MockStrategy(pnl=-100, exit_ts=now - pd.Timedelta(hours=3))
    loss4 = MockStrategy(pnl=-100, exit_ts=now - pd.Timedelta(hours=4))
    # 4 losses in 4 hours window (<= 24h). Should trigger tilt.

    score, details = calculate_discipline_score([loss1, loss2, loss3, loss4], [])
    # 1 tilt event * 5 = -5. Score 95.
    assert score == 95
    assert any("Tilt Detected" in d for d in details)

    # 4. Patience Bonus
    s_a1 = MockStrategy(name="A", hold_days=5, pnl=100)
    s_a2 = MockStrategy(name="A", hold_days=5, pnl=100)
    # Avg = 5.
    s_a3 = MockStrategy(name="A", hold_days=6, pnl=100) # > Avg. Bonus.

    score, details = calculate_discipline_score([s_a1, s_a2, s_a3], [])
    # 1 patience trade * 2 = +2.
    assert score == 100 # Clamped

    # Check patience bonus with penalty
    s_bad = MockStrategy(is_revenge=True) # -10
    # Score = 100 - 10 + 2 = 92
    score, details = calculate_discipline_score([s_a1, s_a2, s_a3, s_bad], [])
    assert score == 92
    assert any("Patience Bonus" in d for d in details)

    # 5. Gamma Risk
    open_pos = [{"dte": 1}, {"dte": 2}]
    score, details = calculate_discipline_score([], open_pos)
    # 2 risks * 5 = -10.
    assert score == 90
    assert any("Gamma Risk" in d for d in details)

def test_calculate_kelly_criterion():
    # PF=2, WR=0.5 -> 0.5 * (1 - 0.5) = 0.25
    assert calculate_kelly_criterion(0.5, 2.0) == 0.25

    # PF=1 -> 0
    assert calculate_kelly_criterion(0.5, 1.0) == 0.0

    # PF=0.5 -> 0
    assert calculate_kelly_criterion(0.5, 0.5) == 0.0

    # WR=0 -> 0
    assert calculate_kelly_criterion(0.0, 2.0) == 0.0

    # WR=1 -> 1 * (1 - 0.5) = 0.5
    assert calculate_kelly_criterion(1.0, 2.0) == 0.5
