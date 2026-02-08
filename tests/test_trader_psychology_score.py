import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.risk_analyzer import calculate_discipline_score

class PsychMockStrategy:
    def __init__(self, net_pnl, entry_ts=None, exit_ts=None, is_revenge=False, strategy_name="TestStrat"):
        self.net_pnl = net_pnl
        self.entry_ts = pd.to_datetime(entry_ts) if entry_ts else None
        self.exit_ts = pd.to_datetime(exit_ts) if exit_ts else None
        self.is_revenge = is_revenge
        self.strategy_name = strategy_name

    def hold_days(self):
        if self.entry_ts and self.exit_ts:
            delta = (self.exit_ts - self.entry_ts).total_seconds()
            return max(delta / 86400.0, 0.001)
        return 0.0

def test_discipline_score_baseline():
    """Verify a perfect score (100) for good behavior (no penalties)."""
    # Create neutral strategies: 1 win, 1 loss (not revenge, reasonable hold times)
    # To avoid early cut bonus or patience bonus, make hold times equal?
    # Or just ensure no penalties trigger.
    # Penalties: Revenge, Tilt (>3 losses in 24h), Gamma Risk.

    start = datetime(2023, 1, 1, 10, 0)
    strategies = [
        PsychMockStrategy(net_pnl=100, entry_ts=start, exit_ts=start + timedelta(days=5)),
        PsychMockStrategy(net_pnl=-50, entry_ts=start, exit_ts=start + timedelta(days=5))
    ]

    # Open positions with safe DTE
    open_positions = [{"dte": 30}]

    score, details = calculate_discipline_score(strategies, open_positions)

    # Bonuses might trigger:
    # Early Loss Cutting: Loss trade hold < avg_hold * 0.5?
    # Avg hold = (5+5)/2 = 5. Loss hold = 5. Not < 2.5. No bonus.
    # Patience Bonus: Win trade hold > avg (per strategy)?
    # Avg for "TestStrat" = (5+5)/2 = 5. Win hold = 5. Not > 5. No bonus.

    assert score == 100
    assert len(details) == 0

def test_tilt_logic():
    """
    Create 4 consecutive losing trades within a 24-hour period.
    Verify the score reflects the tilt penalty.
    """
    base_time = datetime(2023, 1, 1, 10, 0)
    strategies = []

    # Create 4 losses, each 1 hour apart
    for i in range(4):
        entry = base_time + timedelta(hours=i)
        exit_ts = entry + timedelta(minutes=30)
        s = PsychMockStrategy(net_pnl=-100, entry_ts=entry, exit_ts=exit_ts)
        strategies.append(s)

    # Open positions safe
    open_positions = []

    score, details = calculate_discipline_score(strategies, open_positions)

    # Logic:
    # 4 losses in < 24h.
    # i=0: count=1
    # i=1: count=2
    # i=2: count=3
    # i=3: count=4 -> >3 -> Tilt Event!
    # Penalty = 1 * 5 = 5.

    # Also need to check for Early Loss Cutting bonus?
    # Avg hold = 30 mins = 0.02 days.
    # Loss hold = 0.02 days.
    # Is 0.02 < 0.02 * 0.5? No.

    expected_score = 100 - 5
    assert score == expected_score
    assert any("Tilt Detected" in d for d in details)

def test_revenge_logic():
    """
    Create a trade with is_revenge=True.
    Verify score decreases by 10 points per revenge trade.
    Mock scenario: Trade opened < 30 mins after a loss.
    """
    loss_exit = datetime(2023, 1, 1, 10, 0)

    # First trade: Just a loss
    s1 = PsychMockStrategy(net_pnl=-100, entry_ts=loss_exit - timedelta(hours=1), exit_ts=loss_exit)

    # Second trade: Opened 10 mins later (Revenge!)
    revenge_entry = loss_exit + timedelta(minutes=10)
    s2 = PsychMockStrategy(net_pnl=-100, entry_ts=revenge_entry, exit_ts=revenge_entry + timedelta(hours=1), is_revenge=True)

    strategies = [s1, s2]
    open_positions = []

    score, details = calculate_discipline_score(strategies, open_positions)

    # Penalty: 1 revenge trade * 10 = 10.
    # Start: 100 -> 90.

    assert score == 90
    assert any("Revenge Trading" in d for d in details)

def test_patience_bonus():
    """
    Create trades where hold_days for winners > average hold days.
    Verify score increases.
    """
    start = datetime(2023, 1, 1)

    # Strategy 1: Short hold (sets low average)
    s1 = PsychMockStrategy(net_pnl=100, entry_ts=start, exit_ts=start + timedelta(days=2))

    # Strategy 2: Long hold (winner, patience!)
    s2 = PsychMockStrategy(net_pnl=200, entry_ts=start, exit_ts=start + timedelta(days=10))

    # Avg hold = (2 + 10) / 2 = 6 days.
    # s1 hold = 2. 2 > 6? No.
    # s2 hold = 10. 10 > 6? Yes! Patience bonus!

    strategies = [s1, s2]
    open_positions = []

    score, details = calculate_discipline_score(strategies, open_positions)

    # Bonus: 1 patience trade * 2 = +2.
    # However, max score is 100. If we start at 100, it stays 100.
    # Let's add a penalty to see the bonus effect.

    # Add a revenge trade to drop score first
    s3 = PsychMockStrategy(net_pnl=-10, is_revenge=True) # -10 pts
    strategies.append(s3)

    # Recalculate avg hold:
    # s3 has no timestamps -> hold_days = 0.0
    # Avg = (2 + 10 + 0) / 3 = 4.0
    # s1 (2) > 4? No.
    # s2 (10) > 4? Yes. (+2 pts)
    # s3 (0) > 4? No.

    # Score: 100 - 10 (Revenge) + 2 (Patience) = 92.
    # WAIT: s3 (revenge trade) has hold_days=0.0 (default for missing timestamps).
    # Global Avg Hold = 4.0. Half = 2.0.
    # s3 hold (0.0) < 2.0? Yes. This triggers "Early Loss Cutting" bonus (+2).
    # So Total Score = 92 + 2 = 94.

    score, details = calculate_discipline_score(strategies, open_positions)
    assert score == 94
    assert any("Patience Bonus" in d for d in details)
    assert any("Cutting Losses Early" in d for d in details)

def test_gamma_risk():
    """
    Mock open positions with dte <= 3.
    Verify penalty.
    """
    strategies = []
    open_positions = [
        {"dte": 2}, # Risk!
        {"dte": 1}, # Risk!
        {"dte": 10} # Safe
    ]

    score, details = calculate_discipline_score(strategies, open_positions)

    # Penalty: 2 risks * 5 = 10.
    # Score: 100 - 10 = 90.

    assert score == 90
    assert any("Gamma Risk" in d for d in details)

def test_score_clamping():
    """
    Verify score is clamped between 0 and 100.
    """
    # Scenario 1: Excessive penalties -> 0
    strategies = []
    for _ in range(15):
        strategies.append(PsychMockStrategy(net_pnl=-10, is_revenge=True)) # 15 * 10 = 150 penalty

    score, _ = calculate_discipline_score(strategies, [])
    assert score == 0

    # Scenario 2: Excessive bonuses -> 100
    # Start with 0 penalties. Add bonuses.
    # But base is 100. So max is 100.
    strategies = []
    # Create conditions for bonuses
    # ... but if score starts at 100, bonuses don't add above 100.
    # So just verify it doesn't go above 100.

    # Let's create a strategy that earns bonus but no penalties.
    s1 = PsychMockStrategy(net_pnl=100, entry_ts=datetime(2023,1,1), exit_ts=datetime(2023,1,2)) # Hold 1
    s2 = PsychMockStrategy(net_pnl=100, entry_ts=datetime(2023,1,1), exit_ts=datetime(2023,1,10)) # Hold 9
    # Avg = 5. s2 > 5 -> Bonus.

    score, _ = calculate_discipline_score([s1, s2], [])
    assert score == 100
