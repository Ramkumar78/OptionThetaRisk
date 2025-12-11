import pytest
import pandas as pd
from datetime import datetime
from option_auditor.models import StrategyGroup, TradeGroup, Leg
from option_auditor.strategy import _classify_strategy

def make_leg(qty, right, strike, expiry_date="2025-01-01", proceeds=0.0):
    """Helper to create a TradeGroup representing a single leg."""
    # If right is None, it's a Stock leg
    contract_id = f"SYM:{expiry_date}:{right}:{strike}" if right else f"SYM:STOCK"
    expiry = pd.Timestamp(expiry_date) if expiry_date else None

    tg = TradeGroup(
        contract_id=contract_id,
        symbol="SYM",
        expiry=expiry,
        strike=strike,
        right=right
    )
    # Add a dummy execution leg
    tg.add_leg(Leg(ts=pd.Timestamp("2024-01-01 10:00"), qty=qty, price=0.0, fees=0.0, proceeds=proceeds))
    return tg

def make_strategy(legs):
    """Helper to create a StrategyGroup from a list of TradeGroups (legs)."""
    # Use first leg's info for strategy base
    base = legs[0]
    strat = StrategyGroup(id="TEST-STRAT", symbol=base.symbol, expiry=base.expiry)
    for leg in legs:
        strat.add_leg_group(leg)
    return strat

class TestStrategyClassification:

    # --- Single Leg ---
    def test_long_call(self):
        strat = make_strategy([make_leg(1, "C", 100)])
        assert _classify_strategy(strat) == "Long Call"

    def test_short_call(self):
        strat = make_strategy([make_leg(-1, "C", 100)])
        assert _classify_strategy(strat) == "Short Call"

    def test_long_put(self):
        strat = make_strategy([make_leg(1, "P", 100)])
        assert _classify_strategy(strat) == "Long Put"

    def test_short_put(self):
        strat = make_strategy([make_leg(-1, "P", 100)])
        assert _classify_strategy(strat) == "Short Put"
        # Note: "Cash-Secured Put" is treated as Short Put per requirements

    # --- Vertical Spreads ---
    def test_bull_call_spread(self):
        # Long Call lower strike, Short Call higher strike. Debit.
        strat = make_strategy([
            make_leg(1, "C", 100, proceeds=-500),
            make_leg(-1, "C", 110, proceeds=200) # Net Debit -300
        ])
        assert _classify_strategy(strat) == "Bull Call Spread" # Or "Call Vertical (Debit)"

    def test_bear_call_spread(self):
        # Short Call lower strike, Long Call higher strike. Credit.
        strat = make_strategy([
            make_leg(-1, "C", 100, proceeds=500),
            make_leg(1, "C", 110, proceeds=-200) # Net Credit +300
        ])
        assert _classify_strategy(strat) == "Bear Call Spread"

    def test_bull_put_spread(self):
        # Long Put lower strike, Short Put higher strike. Credit.
        # FIX: My previous logic assumed this was Bear Put. Corrected now.
        strat = make_strategy([
            make_leg(1, "P", 100, proceeds=-200),
            make_leg(-1, "P", 110, proceeds=500) # Net Credit +300
        ])
        assert _classify_strategy(strat) == "Bull Put Spread"

    def test_bear_put_spread(self):
        # Short Put lower strike, Long Put higher strike. Debit.
        strat = make_strategy([
            make_leg(-1, "P", 100, proceeds=200),
            make_leg(1, "P", 110, proceeds=-500) # Net Debit -300
        ])
        assert _classify_strategy(strat) == "Bear Put Spread"

    # --- Volatility/Neutral Strategies ---
    def test_long_straddle(self):
        # Long Call + Long Put, same strike
        strat = make_strategy([
            make_leg(1, "C", 100),
            make_leg(1, "P", 100)
        ])
        assert _classify_strategy(strat) == "Long Straddle"

    def test_short_straddle(self):
        # Short Call + Short Put, same strike
        strat = make_strategy([
            make_leg(-1, "C", 100),
            make_leg(-1, "P", 100)
        ])
        assert _classify_strategy(strat) == "Short Straddle"

    def test_long_strangle(self):
        # Long Put (lower), Long Call (higher)
        strat = make_strategy([
            make_leg(1, "P", 90),
            make_leg(1, "C", 110)
        ])
        assert _classify_strategy(strat) == "Long Strangle"

    def test_short_strangle(self):
        # Short Put (lower), Short Call (higher)
        strat = make_strategy([
            make_leg(-1, "P", 90),
            make_leg(-1, "C", 110)
        ])
        assert _classify_strategy(strat) == "Short Strangle"

    def test_iron_condor(self):
        # Bull Put Spread + Bear Call Spread
        # Long Put 90, Short Put 100, Short Call 110, Long Call 120
        strat = make_strategy([
            make_leg(1, "P", 90),
            make_leg(-1, "P", 100),
            make_leg(-1, "C", 110),
            make_leg(1, "C", 120)
        ])
        assert "Iron Condor" in _classify_strategy(strat)

    def test_iron_butterfly(self):
        # Bull Put Spread + Bear Call Spread (Body same strike)
        # Long Put 90, Short Put 100, Short Call 100, Long Call 110
        strat = make_strategy([
            make_leg(1, "P", 90),
            make_leg(-1, "P", 100),
            make_leg(-1, "C", 100),
            make_leg(1, "C", 110)
        ])
        assert "Iron Butterfly" in _classify_strategy(strat)

    # --- Butterflies ---
    def test_long_butterfly_call(self):
        # 1-2-1 Ratio. Buy 1 Low, Sell 2 Mid, Buy 1 High. All Calls.
        strat = make_strategy([
            make_leg(1, "C", 90),
            make_leg(-2, "C", 100),
            make_leg(1, "C", 110)
        ])
        assert _classify_strategy(strat) == "Long Butterfly Spread"

    def test_short_butterfly_put(self):
        # Sell 1 Low, Buy 2 Mid, Sell 1 High. All Puts.
        strat = make_strategy([
            make_leg(-1, "P", 90),
            make_leg(2, "P", 100),
            make_leg(-1, "P", 110)
        ])
        assert _classify_strategy(strat) == "Short Butterfly Spread"

    # --- Time Spreads ---
    def test_calendar_spread(self):
        # Short Near, Long Far. Same Strike. Same Right.
        strat = make_strategy([
            make_leg(-1, "C", 100, expiry_date="2025-01-01"),
            make_leg(1, "C", 100, expiry_date="2025-02-01")
        ])
        assert "Calendar Spread" in _classify_strategy(strat)

    def test_diagonal_spread(self):
        # Short Near/Diff Strike, Long Far. Same Right.
        strat = make_strategy([
            make_leg(-1, "C", 105, expiry_date="2025-01-01"),
            make_leg(1, "C", 100, expiry_date="2025-02-01")
        ])
        assert "Diagonal Spread" in _classify_strategy(strat)

    # --- Ratios ---
    def test_ratio_spread(self):
        # Buy 1, Sell 2. Same Expiry, Diff Strike. Same Right.
        strat = make_strategy([
            make_leg(1, "C", 100),
            make_leg(-2, "C", 105)
        ])
        assert _classify_strategy(strat) == "Ratio Spread"

    # --- Stock Included ---
    def test_covered_call(self):
        # Long Stock + Short Call
        strat = make_strategy([
            make_leg(100, None, None, expiry_date=None), # Stock
            make_leg(-1, "C", 100) # Call
        ])
        # Note: Depending on unit matching (100 shares = 1 contract)
        assert _classify_strategy(strat) == "Covered Call"

    def test_protective_put(self):
        # Long Stock + Long Put
        strat = make_strategy([
            make_leg(100, None, None, expiry_date=None), # Stock
            make_leg(1, "P", 95) # Put
        ])
        assert _classify_strategy(strat) == "Protective Put"

    def test_collar(self):
        # Long Stock + Long Put + Short Call
        strat = make_strategy([
            make_leg(100, None, None, expiry_date=None), # Stock
            make_leg(1, "P", 95), # Put
            make_leg(-1, "C", 105) # Call
        ])
        assert _classify_strategy(strat) == "Collar"

    def test_synthetic_long_stock(self):
        # Long Call + Short Put (ATM)
        strat = make_strategy([
            make_leg(1, "C", 100),
            make_leg(-1, "P", 100)
        ])
        assert _classify_strategy(strat) == "Synthetic Long Stock"

    def test_box_spread(self):
        # Bull Call Spread + Bear Put Spread
        # Long C 90, Short C 110, Long P 110, Short P 90
        strat = make_strategy([
            make_leg(1, "C", 90),
            make_leg(-1, "C", 110),
            make_leg(1, "P", 110),
            make_leg(-1, "P", 90)
        ])
        assert _classify_strategy(strat) == "Box Spread"
