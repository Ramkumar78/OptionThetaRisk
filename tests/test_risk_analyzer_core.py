import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.models import TradeGroup
from option_auditor.risk_analyzer import check_itm_risk, calculate_black_swan_impact

# --- Fixtures ---

@pytest.fixture
def create_trade_group():
    def _create(symbol, qty, strike=None, right=None, expiry=None):
        tg = TradeGroup(
            contract_id=f"{symbol}_{strike}_{right}_{expiry}",
            symbol=symbol,
            expiry=pd.Timestamp(expiry) if expiry else None,
            strike=strike,
            right=right,
            qty_net=qty
        )
        return tg
    return _create

# --- Tests for check_itm_risk ---

def test_check_itm_risk_bull_put_spread(create_trade_group):
    """
    Scenario: Bull Put Spread (Credit Spread)
    - Short Put Strike 100 (Sold)
    - Long Put Strike 90 (Bought for protection)
    - Current Price: 94

    Analysis:
    - Short Put (100): ITM by 6. Intrinsic Value = -6.0 * 100 * 1 = -600.0 (Liability)
    - Long Put (90): OTM. Intrinsic Value = 0.
    - Net Intrinsic: -600.0
    - Threshold: -500.0
    - Result: Risky (True)
    """
    short_put = create_trade_group(symbol="ABC", qty=-1, strike=100, right="P", expiry="2025-01-01")
    long_put = create_trade_group(symbol="ABC", qty=1, strike=90, right="P", expiry="2025-01-01")

    prices = {"ABC": 94.0}

    risky, exposure, details = check_itm_risk([short_put, long_put], prices)

    assert risky is True
    assert exposure == 600.0
    assert len(details) == 1
    assert "Net ITM Exposure -$600" in details[0]

def test_check_itm_risk_bull_put_spread_safe(create_trade_group):
    """
    Scenario: Bull Put Spread (Safe)
    - Short Put Strike 100
    - Long Put Strike 90
    - Current Price: 96

    Analysis:
    - Short Put (100): ITM by 4. Intrinsic = -4.0 * 100 = -400.
    - Net Intrinsic: -400.
    - Threshold: -500.
    - Result: Safe (False) because -400 > -500.
    """
    short_put = create_trade_group(symbol="ABC", qty=-1, strike=100, right="P", expiry="2025-01-01")
    long_put = create_trade_group(symbol="ABC", qty=1, strike=90, right="P", expiry="2025-01-01")

    prices = {"ABC": 96.0}

    risky, exposure, details = check_itm_risk([short_put, long_put], prices)

    assert risky is False
    assert exposure == 0.0
    assert len(details) == 0

def test_check_itm_risk_covered_call(create_trade_group):
    """
    Scenario: Covered Call
    - Long Stock: 100 shares
    - Short Call: Strike 100
    - Current Price: 110

    Analysis:
    - Stock Value: 100 * 110 = +11,000.
    - Short Call (100): ITM by 10. Intrinsic = -10 * 100 = -1,000.
    - Net Liquidation Value: 11,000 - 1,000 = +10,000.
    - Result: Safe (False).
    """
    stock = create_trade_group(symbol="XYZ", qty=100, strike=None, right=None, expiry=None)
    short_call = create_trade_group(symbol="XYZ", qty=-1, strike=100, right="C", expiry="2025-01-01")

    prices = {"XYZ": 110.0}

    risky, exposure, details = check_itm_risk([stock, short_call], prices)

    assert risky is False
    assert exposure == 0.0

def test_check_itm_risk_naked_put(create_trade_group):
    """
    Scenario: Naked Put (Deep ITM)
    - Short Put Strike 100
    - Price: 80

    Analysis:
    - ITM by 20. Intrinsic = -20 * 100 = -2,000.
    - Result: Risky.
    """
    short_put = create_trade_group(symbol="ABC", qty=-1, strike=100, right="P", expiry="2025-01-01")

    prices = {"ABC": 80.0}

    risky, exposure, details = check_itm_risk([short_put], prices)

    assert risky is True
    assert exposure == 2000.0
    assert "Net ITM Exposure -$2,000" in details[0]

def test_check_itm_risk_missing_prices(create_trade_group):
    """
    Scenario: Symbol not in prices dict.
    Should be ignored.
    """
    short_put = create_trade_group(symbol="MISSING", qty=-1, strike=100, right="P", expiry="2025-01-01")
    prices = {"OTHER": 100.0}

    risky, exposure, details = check_itm_risk([short_put], prices)

    assert risky is False
    assert exposure == 0.0
    assert len(details) == 0

# --- Tests for calculate_black_swan_impact ---

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_scenarios(mock_now, create_trade_group):
    """
    Verify all 6 scenarios are present and basic structure is correct.
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")

    stock = create_trade_group(symbol="ABC", qty=100, strike=None, right=None)
    prices = {"ABC": 100.0}

    results = calculate_black_swan_impact([stock], prices)

    assert len(results) == 6
    expected_scenarios = [
        "Market -20%", "Market -10%", "Market -5%",
        "Market +5%", "Market +10%", "Market +20%"
    ]

    scenarios_found = [r.scenario_name for r in results]
    assert scenarios_found == expected_scenarios

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_stock_linear(mock_now, create_trade_group):
    """
    Verify Stock PnL is linear.
    Price 100 -> +20% = 120. Delta = 20. Qty 100 -> PnL +2000.
    Price 100 -> -20% = 80. Delta = -20. Qty 100 -> PnL -2000.
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")

    stock = create_trade_group(symbol="ABC", qty=100, strike=None, right=None)
    prices = {"ABC": 100.0}

    results = calculate_black_swan_impact([stock], prices)

    # Check +20%
    res_plus_20 = next(r for r in results if r.market_move_pct == 20.0)
    assert res_plus_20.portfolio_value_change == pytest.approx(2000.0)
    assert res_plus_20.portfolio_value_change_pct == pytest.approx(20.0)

    # Check -20%
    res_minus_20 = next(r for r in results if r.market_move_pct == -20.0)
    assert res_minus_20.portfolio_value_change == pytest.approx(-2000.0)
    assert res_minus_20.portfolio_value_change_pct == pytest.approx(-20.0)

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_option_convexity(mock_now, create_trade_group):
    """
    Verify Option PnL is non-linear (convex).
    Long Call ATM.
    +20% move should produce profit.
    -20% move should produce loss.
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")
    expiry_date = pd.Timestamp("2025-01-01") # 1 Year to expiry

    # Long Call @ 100. Price 100.
    # Theoretical BS Price will be calculated.
    long_call = create_trade_group(symbol="ABC", qty=1, strike=100, right="C", expiry=expiry_date)
    prices = {"ABC": 100.0}

    results = calculate_black_swan_impact([long_call], prices)

    res_plus_20 = next(r for r in results if r.market_move_pct == 20.0)
    res_minus_20 = next(r for r in results if r.market_move_pct == -20.0)

    # Call gains value as price goes up
    assert res_plus_20.portfolio_value_change > 0

    # Call loses value as price goes down
    assert res_minus_20.portfolio_value_change < 0

    # Convexity check: Profit from +20% should be greater than Loss from -20% (Gamma is positive for Long Call)
    # Note: BS Price at 100 (ATM) approx ~0.4 * 100 * sqrt(1) * 0.4 ~= 16? (roughly)
    # At 120 (ITM), delta increases. At 80 (OTM), delta decreases.
    # So Gain > |Loss|.
    assert res_plus_20.portfolio_value_change > abs(res_minus_20.portfolio_value_change)

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_mixed_portfolio(mock_now, create_trade_group):
    """
    Verify mixed portfolio aggregation (Stock + Option).
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")

    # Stock: 100 shares @ 100. +20% -> +2000.
    stock = create_trade_group(symbol="ABC", qty=100, strike=None, right=None)

    # Short Put: -1 contract @ 100. Price 100.
    # +20% (Price 120): Put value drops (profit for short).
    # -20% (Price 80): Put value rises (loss for short).
    short_put = create_trade_group(symbol="ABC", qty=-1, strike=100, right="P", expiry="2025-01-01")

    prices = {"ABC": 100.0}

    results = calculate_black_swan_impact([stock, short_put], prices)

    res_plus_20 = next(r for r in results if r.market_move_pct == 20.0)

    # Stock gains 2000.
    # Short Put gains (liability decreases).
    # Total gain should be > 2000.
    assert res_plus_20.portfolio_value_change > 2000.0

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_missing_prices(mock_now, create_trade_group):
    """
    Verify missing prices are handled (PnL 0).
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")

    stock = create_trade_group(symbol="MISSING", qty=100, strike=None, right=None)
    prices = {"OTHER": 100.0}

    results = calculate_black_swan_impact([stock], prices)

    for r in results:
        assert r.portfolio_value_change == 0.0
        assert r.portfolio_value_change_pct == 0.0

@patch('option_auditor.risk_analyzer.pd.Timestamp.now')
def test_calculate_black_swan_impact_dict_input(mock_now):
    """
    Verify it handles dictionary inputs as well (legacy/serialized support).
    """
    mock_now.return_value = pd.Timestamp("2024-01-01")

    stock_dict = {
        "symbol": "ABC",
        "qty_net": 100,
        "strike": None,
        "right": None,
        "expiry": None
    }

    prices = {"ABC": 100.0}

    results = calculate_black_swan_impact([stock_dict], prices)

    res_plus_20 = next(r for r in results if r.market_move_pct == 20.0)
    assert res_plus_20.portfolio_value_change == pytest.approx(2000.0)
