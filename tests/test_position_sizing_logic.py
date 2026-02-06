import pytest
from option_auditor.risk_analyzer import calculate_kelly_criterion

def test_kelly_criterion_standard_case():
    # Win rate 50%, Profit Factor 2.0
    # b = 2 * (1-0.5)/0.5 = 2.0
    # Kelly = 0.5 - 0.5/2 = 0.25
    # Simplified: 0.5 * (1 - 1/2) = 0.5 * 0.5 = 0.25
    assert calculate_kelly_criterion(0.5, 2.0) == 0.25

def test_kelly_criterion_break_even():
    # Profit Factor 1.0 -> Expectancy 0 or negative
    assert calculate_kelly_criterion(0.5, 1.0) == 0.0
    assert calculate_kelly_criterion(0.6, 1.0) == 0.0

def test_kelly_criterion_high_win_rate():
    # Win rate 90%, PF 10
    # Simplified: 0.9 * (1 - 1/10) = 0.9 * 0.9 = 0.81
    assert abs(calculate_kelly_criterion(0.9, 10.0) - 0.81) < 1e-6

def test_kelly_criterion_loss_case():
    # PF < 1
    assert calculate_kelly_criterion(0.5, 0.5) == 0.0

def test_kelly_criterion_zero_win_rate():
    assert calculate_kelly_criterion(0.0, 2.0) == 0.0

def test_kelly_criterion_invalid_win_rate():
    assert calculate_kelly_criterion(1.5, 2.0) == 0.0
    assert calculate_kelly_criterion(-0.5, 2.0) == 0.0
