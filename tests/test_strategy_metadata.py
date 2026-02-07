import pytest
from option_auditor.strategy_metadata import calculate_reliability_score, STRATEGY_DETAILS

def test_reliability_score_calculation():
    # Test Turtle Strategy Score
    turtle_details = STRATEGY_DETAILS["Turtle"]
    score = calculate_reliability_score("Turtle", turtle_details)
    # Base 50
    # +10 Stop (2 ATR)
    # +10 Target (4 ATR)
    # +10 Volatility (ATR)
    # +10 Trend (Highs)
    # = 90
    assert score == 90

def test_reliability_score_monte_carlo():
    mc_details = STRATEGY_DETAILS["Monte Carlo"]
    score = calculate_reliability_score("Monte Carlo", mc_details)
    assert score == 85

def test_reliability_score_alpha_101():
    details = STRATEGY_DETAILS["Alpha 101"]
    score = calculate_reliability_score("Alpha 101", details)
    # Base 50
    # +10 Stop
    # +10 Target
    # +10 Volatility (ATR in Target)
    # -5 Single Factor
    # = 75
    assert score == 75

def test_strategy_details_structure():
    for name, details in STRATEGY_DETAILS.items():
        assert "Philosophy" in details
        assert "Reliability_Score" not in details # Should not be in the source dict, added dynamically
