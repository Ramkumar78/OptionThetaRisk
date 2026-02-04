import pytest
from option_auditor.monte_carlo_simulator import MonteCarloSimulator

def test_equity_curves_structure():
    # Setup some dummy trades
    trades = [
        {"return_pct": 5.0},
        {"return_pct": -2.0},
        {"return_pct": 10.0},
        {"return_pct": -5.0},
        {"return_pct": 3.0},
        {"return_pct": 1.0},
        {"return_pct": -1.0},
        {"return_pct": 4.0},
        {"return_pct": 2.0},
        {"return_pct": 6.0}, # 10 trades
    ]

    initial_capital = 10000.0
    sim = MonteCarloSimulator(trades, initial_capital=initial_capital)

    simulations = 100
    result = sim.run(simulations=simulations)

    assert "error" not in result, f"Result contained error: {result.get('error')}"

    # Check if equity_curves key exists
    assert "equity_curves" in result
    curves = result["equity_curves"]

    # Check keys
    expected_keys = ["p05", "p25", "p50", "p75", "p95"]
    for k in expected_keys:
        assert k in curves

    # Check dimensions
    # n_trades = 10. + 1 (initial capital point) = 11 points per curve
    n_points = 11

    for k in expected_keys:
        curve = curves[k]
        assert isinstance(curve, list)
        assert len(curve) == n_points
        # Check initial point is capital
        assert curve[0] == initial_capital

def test_equity_curves_logic():
    # Test with constant positive return, all curves should be identical and increasing
    trades = [{"return_pct": 10.0}] * 10
    sim = MonteCarloSimulator(trades, initial_capital=100.0)
    result = sim.run(simulations=50)

    curves = result["equity_curves"]
    p05 = curves["p05"]
    p95 = curves["p95"]

    # Since all trades are same, all simulations are same path
    assert p05 == p95
    assert p05[-1] > 100.0
    # 100 * (1.1)^10 ~= 259.37
    assert pytest.approx(p05[-1], 0.1) == 259.37
