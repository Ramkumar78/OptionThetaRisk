import pytest
import pandas as pd
from option_auditor.models import StrategyGroup, TradeGroup, Leg

def test_segments_initialization():
    """Verify that 'segments' initializes as an empty list."""
    sg = StrategyGroup(
        id="SG-INIT",
        symbol="AAPL",
        expiry=None
    )
    assert sg.segments == [], "Segments should be initialized as an empty list"
    assert isinstance(sg.segments, list), "Segments should be a list"

def test_add_leg_group():
    """Verify that adding leg groups updates PnL, fees, and timestamps correctly."""
    sg = StrategyGroup(
        id="SG-ADD",
        symbol="SPY",
        expiry=None
    )

    # First TradeGroup (Earlier entry, positive PnL)
    ts1 = pd.Timestamp("2023-01-01 10:00:00")
    # Using different entry/exit for realism
    ts1_entry = ts1
    ts1_exit = ts1 + pd.Timedelta(hours=1)

    tg1 = TradeGroup(
        contract_id="TG-1",
        symbol="SPY",
        expiry=None,
        strike=None,
        right=None,
        pnl=100.0,
        fees=5.0,
        entry_ts=ts1_entry,
        exit_ts=ts1_exit
    )
    # Note: TradeGroup usually computes pnl/fees from legs, but we can set them directly for this test
    # if we don't add legs. However, StrategyGroup just sums up whatever is in TradeGroup.pnl/fees.

    # Second TradeGroup (Later entry, negative PnL)
    ts2 = pd.Timestamp("2023-01-03 10:00:00")
    ts2_entry = ts2
    ts2_exit = ts2 + pd.Timedelta(hours=1)

    tg2 = TradeGroup(
        contract_id="TG-2",
        symbol="SPY",
        expiry=None,
        strike=None,
        right=None,
        pnl=-50.0,
        fees=5.0,
        entry_ts=ts2_entry,
        exit_ts=ts2_exit
    )

    # Add first group
    sg.add_leg_group(tg1)

    assert sg.pnl == 100.0
    assert sg.fees == 5.0
    assert sg.entry_ts == ts1_entry
    assert sg.exit_ts == ts1_exit
    assert len(sg.legs) == 1

    # Add second group
    sg.add_leg_group(tg2)

    # Expected totals:
    # PnL: 100 - 50 = 50.0
    # Fees: 5 + 5 = 10.0
    # Entry TS: min(ts1_entry, ts2_entry) = ts1_entry
    # Exit TS: max(ts1_exit, ts2_exit) = ts2_exit

    assert sg.pnl == 50.0
    assert sg.fees == 10.0
    assert sg.entry_ts == ts1_entry
    assert sg.exit_ts == ts2_exit
    assert len(sg.legs) == 2

    # Test updating timestamps with a middle group
    # A group that starts earlier than current start, but ends before current end
    ts3_entry = pd.Timestamp("2022-12-31 10:00:00") # New earliest start
    ts3_exit = pd.Timestamp("2023-01-01 12:00:00")
    tg3 = TradeGroup(
        contract_id="TG-3",
        symbol="SPY",
        expiry=None,
        strike=None,
        right=None,
        pnl=0.0,
        fees=0.0,
        entry_ts=ts3_entry,
        exit_ts=ts3_exit
    )

    sg.add_leg_group(tg3)

    assert sg.entry_ts == ts3_entry
    assert sg.exit_ts == ts2_exit # Should remain the latest exit

def test_hold_days():
    """Verify hold_days calculation including edge cases."""
    sg = StrategyGroup(
        id="SG-HOLD",
        symbol="QQQ",
        expiry=None
    )

    # Case 1: Missing timestamps
    assert sg.hold_days() == 0.0, "Should return 0.0 when timestamps are missing"

    # Set timestamps
    start_ts = pd.Timestamp("2023-06-01 10:00:00")
    sg.entry_ts = start_ts

    # Still missing exit_ts
    assert sg.hold_days() == 0.0, "Should return 0.0 when exit_ts is missing"

    # Case 2: Identical timestamps (0 duration)
    sg.exit_ts = start_ts
    # Delta is 0. max(0, 0.001) -> 0.001
    assert sg.hold_days() == 0.001, "Should return 0.001 for zero duration"

    # Case 3: Very short duration
    sg.exit_ts = start_ts + pd.Timedelta(seconds=1)
    # Delta = 1 sec = 1/86400 days ≈ 0.00001157 days.
    # Should still return 0.001
    assert sg.hold_days() == 0.001, "Should return 0.001 for very short duration"

    # Case 4: Normal duration (e.g. 2.5 days)
    sg.exit_ts = start_ts + pd.Timedelta(days=2, hours=12)
    expected_days = 2.5
    assert abs(sg.hold_days() - expected_days) < 1e-9, "Should return correct days for normal duration"

def test_average_daily_pnl():
    """Verify average_daily_pnl calculation and division by zero check."""
    # Setup StrategyGroup
    sg = StrategyGroup(
        id="SG-PNL",
        symbol="IWM",
        expiry=None,
        pnl=1050.0,
        fees=50.0 # Net PnL = 1000
    )

    # Case 1: Missing timestamps (hold_days returns 0.0)
    # Expect ZeroDivisionError
    with pytest.raises(ZeroDivisionError):
        _ = sg.average_daily_pnl()

    # Case 2: Very short duration (hold_days returns 0.001)
    start_ts = pd.Timestamp("2023-07-01 10:00:00")
    sg.entry_ts = start_ts
    sg.exit_ts = start_ts # 0 duration

    # Net PnL = 1000
    # Hold Days = 0.001
    # Avg Daily PnL = 1000 / 0.001 = 1,000,000
    expected_pnl = 1000.0 / 0.001
    assert abs(sg.average_daily_pnl() - expected_pnl) < 1e-9, "Should calculate correctly with min hold duration"

    # Case 3: Normal duration
    sg.exit_ts = start_ts + pd.Timedelta(days=5) # 5 days

    # Net PnL = 1000
    # Hold Days = 5
    # Avg Daily PnL = 1000 / 5 = 200
    expected_pnl = 1000.0 / 5.0
    assert abs(sg.average_daily_pnl() - expected_pnl) < 1e-9, "Should calculate correctly for normal duration"
