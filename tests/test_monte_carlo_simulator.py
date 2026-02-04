import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from option_auditor.monte_carlo_simulator import MonteCarloSimulator
from option_auditor.unified_backtester import UnifiedBacktester

def test_monte_carlo_logic():
    # Setup dummy trades
    # 5 trades: +10%, -5%, +10%, -5%, +10%
    trades = [
        {"return_pct": 10.0},
        {"return_pct": -5.0},
        {"return_pct": 10.0},
        {"return_pct": -5.0},
        {"return_pct": 10.0},
    ] * 5 # 25 trades to satisfy min 10 constraint

    initial_capital = 10000.0
    mc = MonteCarloSimulator(trades, initial_capital)

    # Run simulation with small number of sims for speed
    result = mc.run(simulations=100)

    assert "error" not in result
    assert result["initial_capital"] == 10000.0
    assert result["simulations"] == 100
    assert "prob_ruin_50pct" in result
    assert "median_final_equity" in result
    assert "worst_case_drawdown" in result

    # Check basic sanity: with positive drift, median equity should be > initial
    # Avg return per trade is roughly 2.5% arithmetic.
    assert result["median_final_equity"] > 10000.0

    # New assertions for equity curves
    assert "equity_curves" in result
    assert "sample_equity_curves" in result
    assert len(result["sample_equity_curves"]) == 5  # min(100, 5)
    # 25 trades + 1 initial point = 26 points
    assert len(result["equity_curves"]["p50"]) == 26
    assert isinstance(result["sample_equity_curves"], list)
    assert isinstance(result["equity_curves"]["p50"], list)


def test_monte_carlo_not_enough_trades():
    trades = [{"return_pct": 10.0}] # Only 1 trade
    mc = MonteCarloSimulator(trades)
    result = mc.run()
    assert "error" in result
    assert "Not enough trades" in result["error"]

@patch('option_auditor.unified_backtester.UnifiedBacktester.run')
def test_unified_backtester_monte_carlo_integration(mock_run):
    # Setup mock return from backtester
    mock_trade_log = [
        {'type': 'BUY', 'price': 100, 'date': '2023-01-01'},
        {'type': 'SELL', 'price': 110, 'date': '2023-01-05'}, # +10%
        {'type': 'BUY', 'price': 100, 'date': '2023-01-06'},
        {'type': 'SELL', 'price': 90, 'date': '2023-01-10'}, # -10%
    ] * 10 # 20 completed trades

    # Mock run() to populate self.trade_log and return a dummy result
    def side_effect_run():
        backtester.trade_log = mock_trade_log
        return {"trades": 20, "trade_list": []}

    mock_run.side_effect = side_effect_run

    backtester = UnifiedBacktester("SPY", "turtle")
    result = backtester.run_monte_carlo(simulations=50)

    assert mock_run.called
    assert "error" not in result
    assert result["simulations"] == 50
    # Expected return of +10% and -10% is (1.1 * 0.9) = 0.99 per pair. Expect drift down.
    # But checking exact value is hard due to randomness.
    # Just check keys.
    assert "median_drawdown" in result

@patch('option_auditor.unified_backtester.UnifiedBacktester.run')
def test_unified_backtester_monte_carlo_no_trades(mock_run):
    # Mock run() to return empty log
    def side_effect_run():
        backtester.trade_log = []
        return {"trades": 0, "error": "No data found"} # Or just empty result

    mock_run.side_effect = side_effect_run

    backtester = UnifiedBacktester("SPY", "turtle")
    result = backtester.run_monte_carlo()

    assert "error" in result
