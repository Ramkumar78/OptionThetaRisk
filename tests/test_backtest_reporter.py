import pytest
from option_auditor.backtest_reporter import BacktestReporter

def test_max_drawdown_calculation():
    reporter = BacktestReporter()
    # Mock equity curve as requested: [100, 110, 105, 120, 90, 100]
    equity_curve = [100.0, 110.0, 105.0, 120.0, 90.0, 100.0]

    # Calculate drawdown
    result = reporter._calculate_max_drawdown(equity_curve)

    # Assert
    # Peak is 120. Lowest subsequent point is 90.
    # Drop is 120 - 90 = 30.
    # Percentage is 30 / 120 = 0.25 = 25.0%
    assert result == 25.0

def test_max_drawdown_empty():
    reporter = BacktestReporter()
    result = reporter._calculate_max_drawdown([])
    assert result == 0.0

def test_max_drawdown_increasing():
    reporter = BacktestReporter()
    equity_curve = [100, 110, 120, 130]
    result = reporter._calculate_max_drawdown(equity_curve)
    assert result == 0.0

def test_max_drawdown_decreasing():
    reporter = BacktestReporter()
    equity_curve = [100, 90, 80, 50]
    # Peak is 100. Drop to 50 is 50/100 = 50%
    result = reporter._calculate_max_drawdown(equity_curve)
    assert result == 50.0
