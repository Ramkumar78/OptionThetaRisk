import pytest
from datetime import datetime, timedelta
import pandas as pd
from option_auditor.models import TradeGroup, Leg, StrategyGroup, calculate_regulatory_fees

# ----------------------------------------------------------------------------
# TradeGroup Tests
# ----------------------------------------------------------------------------

def test_trade_group_add_leg():
    """Verify that 'pnl', 'fees', 'qty_net', 'entry_ts', and 'exit_ts' update correctly."""
    # Create a TradeGroup
    tg = TradeGroup(
        contract_id="TEST-1",
        symbol="AAPL",
        expiry=None,
        strike=None,
        right=None
    )

    # Leg 1: Entry
    ts1 = pd.Timestamp("2023-01-01 10:00:00")
    leg1 = Leg(
        ts=ts1,
        qty=100.0,
        price=150.0,
        fees=1.0,
        proceeds=-15000.0,  # Buying costs money (negative proceeds usually, but let's follow convention)
        description="Buy 100"
    )

    # Leg 2: Exit
    ts2 = pd.Timestamp("2023-01-02 14:00:00")
    leg2 = Leg(
        ts=ts2,
        qty=-100.0,
        price=155.0,
        fees=1.0,
        proceeds=15500.0,   # Selling gets money
        description="Sell 100"
    )

    # Add first leg
    tg.add_leg(leg1)

    assert tg.pnl == -15000.0
    assert tg.fees == 1.0
    assert tg.qty_net == 100.0
    assert tg.entry_ts == ts1
    assert tg.exit_ts == ts1
    assert len(tg.legs) == 1

    # Add second leg
    tg.add_leg(leg2)

    # Expected totals
    # PnL: -15000 + 15500 = 500
    # Fees: 1 + 1 = 2
    # Qty Net: 100 - 100 = 0
    # Entry TS: min(ts1, ts2) = ts1
    # Exit TS: max(ts1, ts2) = ts2

    assert tg.pnl == 500.0
    assert tg.fees == 2.0
    assert tg.qty_net == 0.0
    assert tg.entry_ts == ts1
    assert tg.exit_ts == ts2
    assert len(tg.legs) == 2


def test_trade_group_check_overtrading():
    """Verify 'is_overtraded' flag flips when legs exceed 'max_legs'."""
    tg = TradeGroup(
        contract_id="TEST-OVER",
        symbol="SPY",
        expiry=None,
        strike=None,
        right=None
    )

    max_legs = 5

    # Add max_legs legs
    for i in range(max_legs):
        tg.add_leg(Leg(pd.Timestamp.now(), 1, 100, 0, 0))

    tg.check_overtrading(max_legs=max_legs)
    assert tg.is_overtraded is False, "Should not be overtraded at exactly max_legs"

    # Add one more leg
    tg.add_leg(Leg(pd.Timestamp.now(), 1, 100, 0, 0))

    tg.check_overtrading(max_legs=max_legs)
    assert tg.is_overtraded is True, "Should be overtraded when legs > max_legs"


# ----------------------------------------------------------------------------
# StrategyGroup Tests
# ----------------------------------------------------------------------------

def test_strategy_group_average_daily_pnl_normal():
    """Test average_daily_pnl with a normal holding period."""
    # Setup StrategyGroup
    sg = StrategyGroup(
        id="SG-1",
        symbol="GOOG",
        expiry=None,
        pnl=1000.0,
        fees=50.0,
        entry_ts=pd.Timestamp("2023-01-01 10:00:00"),
        exit_ts=pd.Timestamp("2023-01-03 10:00:00") # 2 days exactly
    )

    # Net PnL = 1000 - 50 = 950
    # Hold Days = 2.0
    # Avg Daily PnL = 950 / 2.0 = 475.0

    assert sg.net_pnl == 950.0
    assert abs(sg.average_daily_pnl() - 475.0) < 1e-9


def test_strategy_group_average_daily_pnl_min_hold():
    """Test average_daily_pnl with minimal holding period (0.001 constraint)."""
    # Setup StrategyGroup with same entry and exit
    ts = pd.Timestamp("2023-01-01 10:00:00")
    sg = StrategyGroup(
        id="SG-2",
        symbol="TSLA",
        expiry=None,
        pnl=100.0,
        fees=10.0,
        entry_ts=ts,
        exit_ts=ts # 0 seconds diff
    )

    # Net PnL = 90.0
    # Hold Days = max(0, 0.001) = 0.001
    # Avg Daily PnL = 90.0 / 0.001 = 90000.0

    assert sg.net_pnl == 90.0
    assert abs(sg.average_daily_pnl() - 90000.0) < 1e-9

    # Verify logic holds for very small diff < 0.001 days (which is ~86.4 seconds)
    # 1 second diff
    sg.exit_ts = ts + pd.Timedelta(seconds=1)
    # 1/86400 is approx 0.00001157, which is < 0.001
    # Should still use 0.001

    assert abs(sg.average_daily_pnl() - 90000.0) < 1e-9


# ----------------------------------------------------------------------------
# Regulatory Fees Tests
# ----------------------------------------------------------------------------

def test_calculate_regulatory_fees_india():
    """Test India STT: Symbol ending in '.NS' or '.BO' with 'asset_class=stock'."""
    # 0.1% on value
    price = 100.0
    qty = 10
    val = 1000.0
    expected_fee = val * 0.001 # 1.0

    # Test .NS
    fee_ns = calculate_regulatory_fees("RELIANCE.NS", price, qty, action="BUY", asset_class="stock")
    assert abs(fee_ns - expected_fee) < 1e-9

    # Test .BO
    fee_bo = calculate_regulatory_fees("TCS.BO", price, qty, action="SELL", asset_class="stock")
    assert abs(fee_bo - expected_fee) < 1e-9

    # Test non-stock (e.g. option) - Should be 0 based on current logic?
    # Logic: if asset_class.lower() == 'stock': fees += ...
    fee_opt = calculate_regulatory_fees("NIFTY.NS", price, qty, action="BUY", asset_class="option")
    assert fee_opt == 0.0


def test_calculate_regulatory_fees_uk():
    """Test UK Stamp Duty: Symbol ending in '.L' with 'action=BUY' or 'OPEN'."""
    # 0.5% on Buy only
    price = 10.0
    qty = 100
    val = 1000.0
    expected_fee = val * 0.005 # 5.0

    # Test .L with BUY
    fee_buy = calculate_regulatory_fees("LLOY.L", price, qty, action="BUY", asset_class="stock")
    assert abs(fee_buy - expected_fee) < 1e-9

    # Test .L with OPEN
    fee_open = calculate_regulatory_fees("VOD.L", price, qty, action="OPEN", asset_class="stock")
    assert abs(fee_open - expected_fee) < 1e-9

    # Test .L with SELL (Should be 0)
    fee_sell = calculate_regulatory_fees("BARC.L", price, qty, action="SELL", asset_class="stock")
    assert fee_sell == 0.0


def test_calculate_regulatory_fees_us_and_others():
    """Ensure zero fees for US stocks or non-matching actions."""
    price = 150.0
    qty = 10

    # US Stock
    fee_us = calculate_regulatory_fees("AAPL", price, qty, action="BUY", asset_class="stock")
    assert fee_us == 0.0

    # Random suffix
    fee_other = calculate_regulatory_fees("ABC.XYZ", price, qty, action="BUY", asset_class="stock")
    assert fee_other == 0.0
