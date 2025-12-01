from datetime import datetime, timedelta
import pandas as pd
from option_auditor.models import TradeGroup, Leg, StrategyGroup
from option_auditor.strategy import build_strategies, _classify_strategy

def test_grouping_simultaneous_diff_expiry():
    # Test for the fix: Grouping trades with different expirations if time_diff is small.
    # e.g., Calendar Spread opened simultaneously.
    # Or a Roll where we Close A (Buy) and Open B (Sell) simultaneously.

    symbol = "TEST_GROUP"

    t_open = pd.Timestamp("2025-01-01 10:00:00")
    t_open_late = t_open + pd.Timedelta(minutes=3) # Within 5 mins

    expiry_A = pd.Timestamp("2025-01-20")
    expiry_B = pd.Timestamp("2025-02-17")

    rows = [
        # Leg A: Buy (to Close old or Open Long) - Qty +1
        {"contract_id": "A", "datetime": t_open, "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -100.0},
        # Leg B: Sell (to Open new) - Qty -1. 3 mins later.
        {"contract_id": "B", "datetime": t_open_late, "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 200.0},

        # Close/Expirations later (to complete the groups so they are considered)
        # We need to close them to make them "Closed Groups" or rely on them being open?
        # build_strategies processes all groups.

        # Close A (Sell)
        {"contract_id": "A", "datetime": t_open + pd.Timedelta(days=1), "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 50.0},
        # Close B (Buy)
        {"contract_id": "B", "datetime": t_open + pd.Timedelta(days=1), "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -100.0},
    ]
    legs_df = pd.DataFrame(rows)

    strategies = build_strategies(legs_df)

    # Assertions
    # Should be 1 strategy because time_diff (3 mins) < 5 mins

    assert len(strategies) == 1
    strat = strategies[0]

    # Verify classification
    # One Long, One Short, diff expiry, same strike -> Calendar Spread
    assert "Calendar Spread" in strat.strategy_name

def test_grouping_simultaneous_diff_expiry_too_far():
    # Same as above but 10 mins apart. Should NOT group.

    symbol = "TEST_GROUP_FAR"

    t_open = pd.Timestamp("2025-01-01 10:00:00")
    t_open_late = t_open + pd.Timedelta(minutes=10) # > 5 mins

    expiry_A = pd.Timestamp("2025-01-20")
    expiry_B = pd.Timestamp("2025-02-17")

    rows = [
        {"contract_id": "A", "datetime": t_open, "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -100.0},
        {"contract_id": "B", "datetime": t_open_late, "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 200.0},
         # Close
        {"contract_id": "A", "datetime": t_open + pd.Timedelta(days=1), "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 50.0},
        {"contract_id": "B", "datetime": t_open + pd.Timedelta(days=1), "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -100.0},
    ]
    legs_df = pd.DataFrame(rows)

    strategies = build_strategies(legs_df)

    # Should be 2 strategies
    assert len(strategies) == 2
