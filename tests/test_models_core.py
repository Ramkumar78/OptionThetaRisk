import pytest
import pandas as pd
from datetime import datetime
from option_auditor.models import Leg, TradeGroup

def test_leg_initialization():
    """Test initializing a Leg with valid attributes."""
    ts = datetime(2023, 10, 27, 10, 0, 0)
    qty = 10.0
    price = 150.0
    fees = 2.5
    proceeds = -1500.0  # Gross proceeds (price * qty * -1)
    description = "Buy Order"

    leg = Leg(ts=ts, qty=qty, price=price, fees=fees, proceeds=proceeds, description=description)

    assert leg.ts == ts
    assert leg.qty == qty
    assert leg.price == price
    assert leg.fees == fees
    assert leg.proceeds == proceeds
    assert leg.description == description

def test_tradegroup_add_leg():
    """Test adding legs to a TradeGroup and updating aggregated metrics."""
    group = TradeGroup(
        contract_id="C123",
        symbol="AAPL",
        expiry=pd.Timestamp("2023-11-17"),
        strike=150.0,
        right="C"
    )

    ts1 = datetime(2023, 10, 27, 10, 0, 0)
    # Buy 1 @ 5.0. Fees 1.0. Gross Proceeds = -5.0.
    leg1 = Leg(ts=ts1, qty=1.0, price=5.0, fees=1.0, proceeds=-5.0, description="Buy Open")

    group.add_leg(leg1)

    assert len(group.legs) == 1
    assert group.pnl == -5.0
    assert group.fees == 1.0
    assert group.qty_net == 1.0
    assert group.entry_ts == pd.Timestamp(ts1)
    assert group.exit_ts == pd.Timestamp(ts1)

    ts2 = datetime(2023, 10, 28, 14, 0, 0)
    # Sell 1 @ 6.0. Fees 1.0. Gross Proceeds = 6.0.
    leg2 = Leg(ts=ts2, qty=-1.0, price=6.0, fees=1.0, proceeds=6.0, description="Sell Close")

    group.add_leg(leg2)

    assert len(group.legs) == 2
    assert group.pnl == 1.0  # -5.0 + 6.0
    assert group.fees == 2.0   # 1.0 + 1.0
    assert group.qty_net == 0.0
    assert group.net_pnl == -1.0 # 1.0 - 2.0
    assert group.entry_ts == pd.Timestamp(ts1)  # Earliest
    assert group.exit_ts == pd.Timestamp(ts2)   # Latest

def test_tradegroup_is_closed():
    """Test the is_closed property with floating point precision."""
    group = TradeGroup(
        contract_id="C123",
        symbol="AAPL",
        expiry=None,
        strike=None,
        right=None
    )

    # Open position
    group.qty_net = 1.0
    assert group.is_closed is False

    # Closed position
    group.qty_net = 0.0
    assert group.is_closed is True

    # Floating point tolerance test (less than 1e-9)
    group.qty_net = 1e-10
    assert group.is_closed is True

    # Above tolerance
    group.qty_net = 1e-8
    assert group.is_closed is False

def test_check_overtrading():
    """Test overtrading detection based on leg count."""
    group = TradeGroup(
        contract_id="C123",
        symbol="AAPL",
        expiry=None,
        strike=None,
        right=None
    )

    # Add 10 dummy legs
    for _ in range(10):
        group.legs.append(Leg(datetime.now(), 1, 1, 0, 0))

    group.check_overtrading(max_legs=10)
    assert group.is_overtraded is False

    # Add one more leg (total 11)
    group.legs.append(Leg(datetime.now(), 1, 1, 0, 0))
    group.check_overtrading(max_legs=10)
    assert group.is_overtraded is True

    # Test with custom max_legs
    group.is_overtraded = False # Reset
    group.check_overtrading(max_legs=20)
    assert group.is_overtraded is False

def test_tradegroup_net_pnl():
    """Test net_pnl calculation (Gross PnL - Fees)."""
    group = TradeGroup(
        contract_id="C123",
        symbol="AAPL",
        expiry=None,
        strike=None,
        right=None
    )

    group.pnl = 100.0  # Gross PnL
    group.fees = 5.0

    assert group.net_pnl == 95.0
