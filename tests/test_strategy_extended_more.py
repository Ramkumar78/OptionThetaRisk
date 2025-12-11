import pytest
import pandas as pd
from option_auditor.models import StrategyGroup, TradeGroup, Leg
from option_auditor.strategy import _classify_strategy, build_strategies

# --- Fixtures ---

@pytest.fixture
def leg_factory():
    def create_leg(right, strike, qty, proceeds, expiry=None):
        return {
            "right": right,
            "strike": strike,
            "qty": qty,
            "proceeds": proceeds,
            "expiry": expiry,
            "fees": 0.0
        }
    return create_leg

def create_strat(legs_data):
    s = StrategyGroup(id="test", symbol="TEST", expiry=pd.Timestamp.now())
    for ld in legs_data:
        tg = TradeGroup(
            contract_id=f"TEST_{ld.get('strike')}_{ld.get('right')}",
            symbol="TEST",
            expiry=ld.get('expiry'),
            strike=ld.get('strike'),
            right=ld.get('right')
        )
        leg = Leg(
            ts=pd.Timestamp.now(),
            qty=ld['qty'],
            price=0,
            fees=0,
            proceeds=ld['proceeds']
        )
        tg.add_leg(leg)
        s.add_leg_group(tg)
    return s

# --- Classification Tests (Missing Coverage) ---

def test_classify_stock_only():
    s = create_strat([{"right": None, "strike": None, "qty": 100, "proceeds": -100}])
    result = _classify_strategy(s)
    # The source uses a non-breaking hyphen (U+2011)
    assert result == "Multi\u2011leg"

def test_classify_protective_put():
    s = create_strat([
        {"right": None, "strike": None, "qty": 100, "proceeds": -1000}, # Long Stock
        {"right": "P", "strike": 100, "qty": 1, "proceeds": -50, "expiry": pd.Timestamp.now()} # Long Put
    ])
    assert _classify_strategy(s) == "Protective Put"

def test_classify_collar():
    s = create_strat([
        {"right": None, "strike": None, "qty": 100, "proceeds": -1000}, # Long Stock
        {"right": "P", "strike": 90, "qty": 1, "proceeds": -50, "expiry": pd.Timestamp.now()}, # Long Put
        {"right": "C", "strike": 110, "qty": -1, "proceeds": 20, "expiry": pd.Timestamp.now()} # Short Call
    ])
    assert _classify_strategy(s) == "Collar"

def test_classify_diagonal():
    expiry1 = pd.Timestamp("2023-01-01")
    expiry2 = pd.Timestamp("2023-02-01")
    s = create_strat([
        {"right": "C", "strike": 100, "qty": -1, "proceeds": 50, "expiry": expiry1}, # Short front
        {"right": "C", "strike": 105, "qty": 1, "proceeds": -40, "expiry": expiry2} # Long back
    ])
    assert _classify_strategy(s) == "Diagonal Spread"

def test_classify_synthetic_long_stock():
    expiry = pd.Timestamp("2023-01-01")
    s = create_strat([
        {"right": "C", "strike": 100, "qty": 1, "proceeds": -50, "expiry": expiry}, # Long Call
        {"right": "P", "strike": 100, "qty": -1, "proceeds": 40, "expiry": expiry} # Short Put
    ])
    assert _classify_strategy(s) == "Synthetic Long Stock"

def test_classify_strangle():
    expiry = pd.Timestamp("2023-01-01")
    # Long Strangle
    s1 = create_strat([
        {"right": "C", "strike": 110, "qty": 1, "proceeds": -20, "expiry": expiry},
        {"right": "P", "strike": 90, "qty": 1, "proceeds": -20, "expiry": expiry}
    ])
    assert _classify_strategy(s1) == "Long Strangle"

    # Short Strangle
    s2 = create_strat([
        {"right": "C", "strike": 110, "qty": -1, "proceeds": 20, "expiry": expiry},
        {"right": "P", "strike": 90, "qty": -1, "proceeds": 20, "expiry": expiry}
    ])
    assert _classify_strategy(s2) == "Short Strangle"

def test_classify_ratio_spread():
    expiry = pd.Timestamp("2023-01-01")
    s = create_strat([
        {"right": "C", "strike": 100, "qty": 1, "proceeds": -50, "expiry": expiry},
        {"right": "C", "strike": 105, "qty": -2, "proceeds": 60, "expiry": expiry}
    ])
    assert _classify_strategy(s) == "Ratio Spread"

def test_classify_butterfly():
    expiry = pd.Timestamp("2023-01-01")
    # Long Butterfly: 1 Long ITM, 2 Short ATM, 1 Long OTM (Call)
    # Body is short 2x. Wings long 1x.
    s = create_strat([
        {"right": "C", "strike": 90, "qty": 1, "proceeds": -10, "expiry": expiry},
        {"right": "C", "strike": 100, "qty": -2, "proceeds": 15, "expiry": expiry},
        {"right": "C", "strike": 110, "qty": 1, "proceeds": -2, "expiry": expiry}
    ])
    assert _classify_strategy(s) == "Long Butterfly Spread"

def test_classify_iron_butterfly():
    expiry = pd.Timestamp("2023-01-01")
    # Short Put ATM, Short Call ATM, Long Put OTM, Long Call OTM
    # Strikes: P(Short)=100, C(Short)=100, P(Long)=90, C(Long)=110
    s = create_strat([
        {"right": "P", "strike": 90, "qty": 1, "proceeds": -5, "expiry": expiry},
        {"right": "P", "strike": 100, "qty": -1, "proceeds": 10, "expiry": expiry},
        {"right": "C", "strike": 100, "qty": -1, "proceeds": 10, "expiry": expiry},
        {"right": "C", "strike": 110, "qty": 1, "proceeds": -5, "expiry": expiry}
    ])
    assert _classify_strategy(s) == "Iron Butterfly"

def test_classify_box_spread():
    expiry = pd.Timestamp("2023-01-01")
    # Bull Call Spread + Bear Put Spread at same strikes
    # Long Call 100, Short Call 110
    # Long Put 110, Short Put 100
    s = create_strat([
        {"right": "C", "strike": 100, "qty": 1, "proceeds": -10, "expiry": expiry},
        {"right": "C", "strike": 110, "qty": -1, "proceeds": 5, "expiry": expiry},
        {"right": "P", "strike": 100, "qty": -1, "proceeds": 5, "expiry": expiry},
        {"right": "P", "strike": 110, "qty": 1, "proceeds": -10, "expiry": expiry}
    ])
    assert _classify_strategy(s) == "Box Spread"

def test_classify_vertical_put_with_stock():
    expiry = pd.Timestamp("2023-01-01")
    # Short Stock + Bull Put Spread to force positive proceeds
    # This falls through the Stock+Option check (not a collar/protective put)
    # And falls through num_opt only check
    # But hits the "num_opt == 2" block at the end
    s = create_strat([
        {"right": None, "strike": None, "qty": -100, "proceeds": 1000}, # Short Stock (Credit)
        {"right": "P", "strike": 100, "qty": -1, "proceeds": 50, "expiry": expiry}, # Short Put
        {"right": "P", "strike": 90, "qty": 1, "proceeds": -20, "expiry": expiry} # Long Put
    ])
    # Net proceeds = 1000 + 50 - 20 = 1030 > 0 (Credit)
    assert _classify_strategy(s) == "Put Vertical (Credit)"

# --- Wheel Strategy Logic Tests ---

def test_wheel_strategy_detection():
    # 1. Short Put (assigned)
    # 2. Long Stock (opened via assignment)

    t1 = pd.Timestamp("2023-01-01 10:00")
    t2 = pd.Timestamp("2023-01-15 16:00") # Expiry/Assignment

    legs = []
    # Short Put: Open
    legs.append({"datetime": t1, "contract_id": "P1", "symbol": "XYZ", "qty": -1, "proceeds": 100, "fees": 1, "strike": 100, "right": "P", "expiry": t2})
    # Short Put: Close (by assignment - strictly speaking, option disappears, but we model it as closed)
    # Wait, build_strategies logic for wheel looks for "Short Puts that are CLOSED"
    # Usually assignment doesn't generate a closing transaction for the option in some brokers, but parser handles it?
    # Assume we have a closing transaction or it's expired.
    legs.append({"datetime": t2, "contract_id": "P1", "symbol": "XYZ", "qty": 1, "proceeds": 0, "fees": 0, "strike": 100, "right": "P", "expiry": t2})

    # Stock Acquisition (Assignment)
    t3 = t2 + pd.Timedelta(hours=1) # Same day assignment
    legs.append({"datetime": t3, "contract_id": "STOCK", "symbol": "XYZ", "qty": 100, "proceeds": -10000, "fees": 5, "strike": None, "right": None, "expiry": None})

    df = pd.DataFrame(legs)
    strategies = build_strategies(df)

    # Should detect Wheel
    assert len(strategies) == 1
    assert strategies[0].strategy_name == "Wheel"
    # PnL check: Stock cost basis reduced by Put premium.
    # Stock PnL = -10000. Put PnL = 100.
    # Total PnL = -9900 (Unrealized)
    assert strategies[0].pnl == -9900.0

def test_revenge_trading_logic():
    # Trade 1: Loss
    t1 = pd.Timestamp("2023-01-01 10:00")
    t2 = pd.Timestamp("2023-01-01 11:00")

    # Trade 2: Opens 2 mins later
    t3 = pd.Timestamp("2023-01-01 11:02")
    t4 = pd.Timestamp("2023-01-01 12:00")

    legs = []
    # Trade 1 (Loss)
    legs.append({"datetime": t1, "contract_id": "C1", "symbol": "XYZ", "qty": 1, "proceeds": -100, "fees": 0, "strike": 100, "right": "C", "expiry": t4})
    legs.append({"datetime": t2, "contract_id": "C1", "symbol": "XYZ", "qty": -1, "proceeds": 50, "fees": 0, "strike": 100, "right": "C", "expiry": t4})

    # Trade 2
    legs.append({"datetime": t3, "contract_id": "C2", "symbol": "XYZ", "qty": 1, "proceeds": -100, "fees": 0, "strike": 100, "right": "C", "expiry": t4})
    legs.append({"datetime": t4, "contract_id": "C2", "symbol": "XYZ", "qty": -1, "proceeds": 150, "fees": 0, "strike": 100, "right": "C", "expiry": t4})

    df = pd.DataFrame(legs)
    strategies = build_strategies(df)

    # Logic says: If previous trade was Loss, roll window tightens to 1 min.
    # Here gap is 2 min. So they should NOT merge.
    # Trade 1 PnL = -50 (Loss).
    # Gap = 2 min.
    # Should be 2 strategies.

    assert len(strategies) == 2
    assert strategies[0].net_pnl < 0

def test_roll_logic_merge():
    # Trade 1: Win
    t1 = pd.Timestamp("2023-01-01 10:00")
    t2 = pd.Timestamp("2023-01-01 11:00")

    # Trade 2: Opens 5 mins later (Roll)
    t3 = pd.Timestamp("2023-01-01 11:05")
    t4 = pd.Timestamp("2023-01-01 12:00")

    legs = []
    # Trade 1 (Win)
    legs.append({"datetime": t1, "contract_id": "C1", "symbol": "XYZ", "qty": 1, "proceeds": -100, "fees": 0, "strike": 100, "right": "C", "expiry": t4})
    legs.append({"datetime": t2, "contract_id": "C1", "symbol": "XYZ", "qty": -1, "proceeds": 150, "fees": 0, "strike": 100, "right": "C", "expiry": t4})

    # Trade 2
    legs.append({"datetime": t3, "contract_id": "C2", "symbol": "XYZ", "qty": 1, "proceeds": -100, "fees": 0, "strike": 100, "right": "C", "expiry": t4})
    legs.append({"datetime": t4, "contract_id": "C2", "symbol": "XYZ", "qty": -1, "proceeds": 150, "fees": 0, "strike": 100, "right": "C", "expiry": t4})

    df = pd.DataFrame(legs)
    strategies = build_strategies(df)

    # Trade 1 PnL = +50.
    # Gap = 5 min. < 15 min default window.
    # Should merge into "Rolled ..."

    assert len(strategies) == 1
    assert "Rolled" in strategies[0].strategy_name
