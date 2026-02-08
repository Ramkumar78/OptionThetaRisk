from hypothesis import given, strategies as st, settings, HealthCheck
from option_auditor.models import calculate_regulatory_fees, StrategyGroup, TradeGroup
from option_auditor.risk_analyzer import calculate_discipline_score
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- Tests for calculate_regulatory_fees ---

@given(
    symbol=st.text(min_size=1),
    price=st.floats(min_value=0.01, max_value=10000.0),
    qty=st.floats(min_value=0.01, max_value=10000.0),
    action=st.sampled_from(['BUY', 'SELL', 'OPEN', 'CLOSE']),
    asset_class=st.sampled_from(['stock', 'option', 'future'])
)
def test_regulatory_fees_properties(symbol, price, qty, action, asset_class):
    fees = calculate_regulatory_fees(symbol, price, qty, action, asset_class)

    # Property 1: Fees should never be negative
    assert fees >= 0.0

    # Property 2: Non-UK/India symbols should have 0 fees
    if not (symbol.endswith('.NS') or symbol.endswith('.BO') or symbol.endswith('.L')):
        assert fees == 0.0

    # Property 3: Options on UK stocks should have 0 fees (Stamp Duty is on stock only)
    if symbol.endswith('.L') and asset_class != 'stock':
        assert fees == 0.0

    # Property 4: India options should have 0 fees (function currently only implements STT on stock delivery)
    if (symbol.endswith('.NS') or symbol.endswith('.BO')) and asset_class != 'stock':
        assert fees == 0.0


# --- Tests for calculate_discipline_score ---

# Helper to generate StrategyGroup mocks
@st.composite
def strategy_group_strategy(draw):
    s = StrategyGroup(
        id="test",
        symbol="TEST",
        expiry=None
    )
    # We cheat a bit and inject properties needed by calculate_discipline_score
    # The function checks: is_revenge, net_pnl, hold_days(), exit_ts, entry_ts

    s.is_revenge = draw(st.booleans())
    s.pnl = draw(st.floats(min_value=-1000, max_value=1000))
    s.fees = 0.0 # Simplify

    # Create valid timestamps
    exit_dt = draw(st.datetimes(min_value=datetime(2023, 1, 1), max_value=datetime(2024, 1, 1)))
    hold_duration = draw(st.timedeltas(min_value=timedelta(minutes=1), max_value=timedelta(days=100)))
    entry_dt = exit_dt - hold_duration

    s.entry_ts = pd.Timestamp(entry_dt)
    s.exit_ts = pd.Timestamp(exit_dt)

    # Mock hold_days method by attaching it or ensuring the class method works
    # StrategyGroup.hold_days uses entry_ts and exit_ts, so it should work fine.

    return s

@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(
    strategies=st.lists(strategy_group_strategy(), max_size=10),
    open_positions=st.lists(st.dictionaries(
        keys=st.sampled_from(['dte', 'symbol']),
        values=st.one_of(st.integers(min_value=-1, max_value=100), st.text())
    ), max_size=5)
)
def test_discipline_score_properties(strategies, open_positions):
    score, details = calculate_discipline_score(strategies, open_positions)

    # Property 1: Score must be between 0 and 100
    assert 0 <= score <= 100

    # Property 2: Details should be a list of strings
    assert isinstance(details, list)
    for d in details:
        assert isinstance(d, str)

def test_discipline_score_revenge_penalty():
    # Deterministic test for revenge penalty
    s1 = StrategyGroup(id="1", symbol="A", expiry=None)
    s1.is_revenge = True
    s1.pnl = -100
    s1.entry_ts = pd.Timestamp("2023-01-01")
    s1.exit_ts = pd.Timestamp("2023-01-02") # 1 day hold

    # With 1 revenge trade, score starts at 100, -10 = 90.
    # Does it trigger other bonuses?
    # Avg hold = 1.0. s1 hold = 1.0. Not < 0.5 * avg. No early cut bonus.
    # Patience bonus? Pnl < 0. No.
    # Tilt? Only 1 loss. No.

    score, details = calculate_discipline_score([s1], [])
    assert score == 90
    assert any("Revenge Trading" in d for d in details)
