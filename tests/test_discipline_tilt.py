import pytest
import pandas as pd
from datetime import datetime, timedelta
from option_auditor.risk_analyzer import calculate_discipline_score

class MockStrategy:
    def __init__(self, net_pnl, exit_ts=None, strategy_name="TestStrat", hold_days_val=1.0, is_revenge=False):
        self.net_pnl = net_pnl
        self.exit_ts = pd.Timestamp(exit_ts) if exit_ts else None
        self.strategy_name = strategy_name
        self._hold_days = hold_days_val
        self.is_revenge = is_revenge

    def hold_days(self):
        return self._hold_days

def test_tilt_detection():
    # Setup: Create 4 losses within 24 hours
    base_time = datetime(2023, 1, 1, 10, 0, 0)

    losses = []
    # 4 losses, 1 hour apart
    for i in range(4):
        losses.append(MockStrategy(
            net_pnl=-100,
            exit_ts=base_time + timedelta(hours=i)
        ))

    # Initial score should be 100
    # Tilt detection triggers on >3 losses in 24h.
    # Here we have 4. So count=4 for the last one?
    # No, for i=3 (4th trade), window includes i=0,1,2. So count=4.
    # Trigger!

    score, details = calculate_discipline_score(losses, [])

    # Expected penalty: 1 event * 5 = 5. Score = 95.
    assert score == 95, f"Expected score 95, got {score}. Details: {details}"
    assert any("Tilt Detected" in d for d in details)

    # Add a 5th loss 2 hours later
    losses.append(MockStrategy(
        net_pnl=-100,
        exit_ts=base_time + timedelta(hours=6)
    ))

    # Now we have 5 losses in 6 hours.
    # i=3 triggers (count=4)
    # i=4 triggers (count=5)
    # Total penalty: 5 + 5 = 10. Score = 90.

    score, details = calculate_discipline_score(losses, [])
    assert score == 90, f"Expected score 90, got {score}. Details: {details}"

def test_patience_bonus():
    # Setup: 3 strategies. Avg hold = (10 + 20 + 30) / 3 = 20.
    # Strat 1: Win, hold 10 (below avg) -> No bonus
    # Strat 2: Win, hold 20 (equal avg) -> No bonus
    # Strat 3: Win, hold 30 (above avg) -> Bonus

    strats = [
        MockStrategy(net_pnl=100, hold_days_val=10),
        MockStrategy(net_pnl=100, hold_days_val=20),
        MockStrategy(net_pnl=100, hold_days_val=30),
    ]

    # To test bonus, let's introduce a penalty first to avoid capping at 100.
    # Add a revenge trade (-10). Set hold_days=10 to avoid "Cutting Losses Early" bonus.
    strats.append(MockStrategy(net_pnl=-10, is_revenge=True, hold_days_val=10))

    # Avg hold calculation includes the revenge trade
    # Holds: 10, 20, 30, 10. Avg = 70/4 = 17.5.
    # Strat 1 (10) < 17.5 -> No
    # Strat 2 (20) > 15.25 -> Bonus!
    # Strat 3 (30) > 17.5 -> Bonus!
    # Total 2 bonuses. +4 points.

    # Initial: 100
    # Penalty: -10 -> 90.
    # Bonus: +4 -> 94.
    # "Cutting Losses Early": Avg * 0.5 = 8.75. Revenge hold 10 > 8.75. No bonus.

    score, details = calculate_discipline_score(strats, [])
    assert score == 94, f"Expected score 94, got {score}. Details: {details}"
    assert any("Patience Bonus" in d for d in details)

def test_mixed_scenario():
    # Tilt + Patience
    base_time = datetime(2023, 1, 1, 10, 0, 0)

    strats = []
    # 4 rapid losses (Tilt) -> -5
    # Set hold_days=2 to avoid "Cutting Losses Early"
    for i in range(4):
        strats.append(MockStrategy(
            net_pnl=-100,
            exit_ts=base_time + timedelta(hours=i),
            hold_days_val=2
        ))

    # 1 long held winner (Patience)
    # Avg hold of losses = 2.
    # Winner hold = 10. Avg overall = (4*2 + 10)/5 = 3.6.
    # Avg * 0.5 = 1.8. Loss hold (2) > 1.8. No early cut bonus.
    # Winner > Avg. -> +2.

    strats.append(MockStrategy(
        net_pnl=500,
        exit_ts=base_time + timedelta(hours=10),
        hold_days_val=10
    ))

    # Score start 100.
    # Tilt: -5.
    # Patience: +2.
    # Result: 97.

    score, details = calculate_discipline_score(strats, [])
    assert score == 97, f"Expected score 97, got {score}. Details: {details}"
    assert any("Tilt Detected" in d for d in details)
    assert any("Patience Bonus" in d for d in details)

def test_tilt_boundary():
    # Exactly 3 losses in 24h -> No penalty
    base_time = datetime(2023, 1, 1, 10, 0, 0)
    losses = []
    for i in range(3):
        losses.append(MockStrategy(
            net_pnl=-100,
            exit_ts=base_time + timedelta(hours=i)
        ))

    score, details = calculate_discipline_score(losses, [])
    assert score == 100
    assert not any("Tilt Detected" in d for d in details)

    # 4th loss 25 hours later -> No penalty (window only has 1)
    losses.append(MockStrategy(
        net_pnl=-100,
        exit_ts=base_time + timedelta(hours=25)
    ))
    score, details = calculate_discipline_score(losses, [])
    assert score == 100
