import pytest
import pandas as pd
from unittest.mock import MagicMock
from option_auditor.risk_analyzer import calculate_discipline_score

def create_mock_strategy(net_pnl, hold_days_val, exit_ts=None, is_revenge=False, strategy_name="Test"):
    """
    Helper to create a mock strategy object with required attributes.
    """
    mock = MagicMock()
    mock.net_pnl = net_pnl
    # Mock hold_days() method
    mock.hold_days.return_value = float(hold_days_val)
    mock.exit_ts = pd.to_datetime(exit_ts) if exit_ts else None
    mock.is_revenge = is_revenge
    mock.strategy_name = strategy_name
    return mock

def test_baseline_score():
    """
    Verify that an empty list of strategies and open positions returns a perfect score (100).
    """
    score, details = calculate_discipline_score([], [])
    assert score == 100
    assert details == []

def test_revenge_trading_penalty():
    """
    Verify that revenge trading strategies reduce the score by 10 points per instance.
    """
    # Create 3 revenge trades (loss or win doesn't matter for revenge flag, usually loss)
    s1 = create_mock_strategy(-100, 1.0, is_revenge=True)
    s2 = create_mock_strategy(-100, 1.0, is_revenge=True)
    s3 = create_mock_strategy(100, 1.0, is_revenge=True) # Even a win can be flagged as revenge

    strategies = [s1, s2, s3]
    score, details = calculate_discipline_score(strategies, [])

    # Expected: 100 - (3 * 10) = 70
    assert score == 70
    assert len(details) == 1
    assert "Revenge Trading: -30 pts (3 instances)" in details[0]

def test_tilt_penalty_logic():
    """
    Verify penalty for 'Tilt' (rapid losses in 24h window).
    Logic: >3 losses in 24h window triggers tilt event.
    """
    base_time = pd.Timestamp("2023-01-01 10:00:00")

    # Create 5 losses, each 1 hour apart
    # T=0, T+1, T+2, T+3, T+4
    # Window is 24h.
    # Loss 1: count=1
    # Loss 2: count=2
    # Loss 3: count=3
    # Loss 4: count=4 -> Tilt Event 1
    # Loss 5: count=5 -> Tilt Event 2

    strategies = []
    for i in range(5):
        t = base_time + pd.Timedelta(hours=i)
        s = create_mock_strategy(-100, 1.0, exit_ts=t)
        strategies.append(s)

    score, details = calculate_discipline_score(strategies, [])

    # Expected: 2 tilt events * 5 pts = 10 pts penalty
    # Score: 100 - 10 = 90
    assert score == 90
    assert any("Tilt Detected" in d for d in details)
    assert "-10 pts" in details[0]

def test_early_loss_cutting_bonus():
    """
    Verify bonus for cutting losses early (< 50% of avg hold time).
    """
    # 1. Establish Average Hold Time
    # S1: Hold 10
    # S2: Hold 10
    # Avg = 10. Threshold for early cut = 5.
    # Note: Make them losses to avoid triggering 'Patience Bonus' (holding winners > avg)
    # which would confound the test result.
    s1 = create_mock_strategy(-10, 10.0)
    s2 = create_mock_strategy(-10, 10.0)

    # 2. Add Early Cut Loss
    # S3: Hold 2 (< 5), Loss
    s3 = create_mock_strategy(-50, 2.0)

    # 3. Add a penalty to make room for bonus (otherwise capped at 100)
    # Add a Revenge Trade (-10 pts)
    s4 = create_mock_strategy(-50, 2.0, is_revenge=True)

    strategies = [s1, s2, s3, s4]

    # Calculation:
    # Base: 100
    # Revenge: -10 -> 90
    # Early Cut Bonus:
    #   Avg Hold = (10+10+2+2)/4 = 6.0?
    #   Wait, average calculation includes ALL strategies in the input list.
    #   Let's re-calculate avg hold with s3 and s4 included.
    #   Holds: 10, 10, 2, 2. Mean = 24 / 4 = 6.0.
    #   Threshold = 6.0 * 0.5 = 3.0.
    #   S3 hold 2.0 < 3.0 -> Bonus.
    #   S4 hold 2.0 < 3.0 -> Bonus.
    #   Total Early Cuts = 2.
    #   Bonus = 2 * 2 = 4 pts.
    # Final Score: 100 - 10 + 4 = 94.

    score, details = calculate_discipline_score(strategies, [])

    assert score == 94
    # Check details for both entries
    assert any("Revenge Trading" in d for d in details)
    assert any("Cutting Losses Early" in d for d in details)
    assert "+4 pts" in [d for d in details if "Cutting Losses" in d][0]

def test_patience_bonus():
    """
    Verify bonus for holding winners longer than average (Patience).
    """
    # Strategy 'A': Avg hold needs to be established.
    # S1: Hold 5, Loss (sets baseline for 'A')
    s1 = create_mock_strategy(-10, 5.0, strategy_name="A")

    # S2: Hold 10, Win (10 > 5? Yes -> Patience Bonus)
    s2 = create_mock_strategy(100, 10.0, strategy_name="A")

    # Add penalty to see bonus
    s3 = create_mock_strategy(-10, 5.0, is_revenge=True, strategy_name="B")

    strategies = [s1, s2, s3]

    # Avg Hold for 'A': (5 + 10) / 2 = 7.5?
    # Code:
    # strategy_hold_avgs[name].append(s.hold_days())
    # avg_map = {k: mean(v)}
    # 'A': mean([5, 10]) = 7.5.
    # S2 hold 10 > 7.5? Yes. Bonus.
    # S1 is loss (no bonus).
    # S3 is 'B' (no avg to compare? avg_map['B'] = 5. S3 is loss anyway).

    # Wait, S2 is included in the average calculation.
    # So Avg for A is 7.5.
    # S2 (10) > 7.5 -> Yes.

    # Score:
    # Base 100
    # Revenge (S3): -10 -> 90.
    # Patience (S2): +2 -> 92.

    score, details = calculate_discipline_score(strategies, [])

    assert score == 92
    assert any("Patience Bonus" in d for d in details)

def test_gamma_risk_penalty():
    """
    Verify penalty for holding positions with < 3 DTE.
    """
    open_positions = [
        {'dte': 3, 'symbol': 'AAPL'}, # Penalty
        {'dte': 1, 'symbol': 'TSLA'}, # Penalty
        {'dte': 10, 'symbol': 'MSFT'}, # No Penalty
        {'dte': None, 'symbol': 'CASH'} # Ignore
    ]

    # 2 penalties * 5 = 10 pts.
    score, details = calculate_discipline_score([], open_positions)

    assert score == 90
    assert any("Gamma Risk" in d for d in details)
    assert "-10 pts" in [d for d in details if "Gamma Risk" in d][0]

def test_score_clamping():
    """
    Verify score stays within 0-100 range.
    """
    # Case 1: Excessive Penalties -> 0
    # 15 Revenge trades = -150 pts.
    strats_bad = [create_mock_strategy(-10, 1.0, is_revenge=True) for _ in range(15)]
    score_min, _ = calculate_discipline_score(strats_bad, [])
    assert score_min == 0

    # Case 2: Bonuses on top of 100 -> 100
    # 10 Early Cuts (+20 pts). Base 100.
    # Need to manipulate average hold.
    # S_base: Hold 20.
    # S_cuts: Hold 1 (1 < 10).
    s_base = [create_mock_strategy(100, 20.0) for _ in range(5)]
    s_cuts = [create_mock_strategy(-10, 1.0) for _ in range(5)]
    # Avg ~10. 1 < 5. All 5 are early cuts. Bonus +10.
    # Score 110 -> Clamp 100.

    score_max, details = calculate_discipline_score(s_base + s_cuts, [])
    assert score_max == 100
    # Ensure bonus was actually calculated
    assert any("Cutting Losses Early" in d for d in details)
