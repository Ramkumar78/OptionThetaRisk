from datetime import datetime, timedelta
import pandas as pd
from option_auditor.models import TradeGroup, Leg, StrategyGroup
from option_auditor.strategy import build_strategies, _classify_strategy

def test_rolling_logic_different_expiration():
    # Setup:
    # Trade A: Short Put Jan 20. Opened Jan 1. Closed Jan 15.
    # Trade B: Short Put Feb 17. Opened Jan 15 (Simultaneous with closing A).
    # Result should be "Rolled ..." and combined PnL.

    # Symbols
    symbol = "TEST"

    # Dates
    t_open_A = pd.Timestamp("2025-01-01 10:00:00")
    t_close_A = pd.Timestamp("2025-01-15 10:00:00")
    t_open_B = pd.Timestamp("2025-01-15 10:00:00") + pd.Timedelta(seconds=30) # Within 5 mins
    t_close_B = pd.Timestamp("2025-02-01 10:00:00")

    expiry_A = pd.Timestamp("2025-01-20")
    expiry_B = pd.Timestamp("2025-02-17")

    # Trade A (Closed)
    # Sell to Open
    leg1 = Leg(ts=t_open_A, qty=-1, price=1.0, fees=0, proceeds=100.0)
    # Buy to Close
    leg2 = Leg(ts=t_close_A, qty=1, price=1.5, fees=0, proceeds=-150.0)

    groupA = TradeGroup(contract_id="A", symbol=symbol, expiry=expiry_A, strike=100, right="P")
    groupA.add_leg(leg1)
    groupA.add_leg(leg2)
    # Net PnL A = -50

    # Trade B (New Open)
    # Sell to Open (Roll)
    leg3 = Leg(ts=t_open_B, qty=-1, price=2.0, fees=0, proceeds=200.0)
    # Buy to Close (Later)
    leg4 = Leg(ts=t_close_B, qty=1, price=0.5, fees=0, proceeds=-50.0)

    groupB = TradeGroup(contract_id="B", symbol=symbol, expiry=expiry_B, strike=100, right="P")
    groupB.add_leg(leg3)
    groupB.add_leg(leg4)
    # Net PnL B = +150

    # To test build_strategies, we normally pass a dataframe of legs.
    # But build_strategies does grouping logic internally.
    # Actually, build_strategies takes `legs_df`.
    # Let's construct `legs_df` that mimics this.

    rows = [
        # A Open
        {"contract_id": "A", "datetime": t_open_A, "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 100.0},
        # A Close
        {"contract_id": "A", "datetime": t_close_A, "symbol": symbol, "expiry": expiry_A, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -150.0},
        # B Open
        {"contract_id": "B", "datetime": t_open_B, "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": -1, "fees": 0, "proceeds": 200.0},
        # B Close
        {"contract_id": "B", "datetime": t_close_B, "symbol": symbol, "expiry": expiry_B, "strike": 100, "right": "P", "qty": 1, "fees": 0, "proceeds": -50.0},
    ]
    legs_df = pd.DataFrame(rows)

    strategies = build_strategies(legs_df)

    # Assertions
    # Should be 1 strategy because of rolling logic
    assert len(strategies) == 1
    strat = strategies[0]

    # Name should indicate rolling
    assert "Rolled" in strat.strategy_name

    # Total PnL should be -50 + 150 = 100
    assert strat.pnl == 100.0
