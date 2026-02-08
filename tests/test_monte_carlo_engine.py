import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.monte_carlo_simulator import MonteCarloSimulator, run_simple_monte_carlo

class TestMonteCarloSimulator:
    def test_run_basic_success(self):
        """Test basic successful run with valid inputs."""
        trades = [{'return_pct': 5.0} for _ in range(20)]
        sim = MonteCarloSimulator(trades, initial_capital=10000.0)

        # Mock RNG to ensure deterministic behavior
        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            # Mock integers for index selection: always pick index 0
            # Shape: (simulations, n_trades)
            # We'll simulate 100 runs
            simulations = 100
            n_trades = 20
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)

            # Mock choice for sample curves: pick first 5
            mock_gen.choice.return_value = np.arange(5)

            result = sim.run(simulations=simulations)

            assert "error" not in result
            assert result["simulations"] == simulations
            assert result["initial_capital"] == 10000.0

            # With 5% return every time:
            # Final equity = 10000 * (1.05)^20
            expected_final = 10000.0 * (1.05 ** 20)
            # Check median final equity (all are same)
            assert result["median_final_equity"] == pytest.approx(expected_final, rel=1e-2)

            # Drawdown should be 0 because it only goes up
            assert result["median_drawdown"] == 0.0

    def test_run_insufficient_trades(self):
        """Test error when fewer than 10 trades provided."""
        trades = [{'return_pct': 5.0} for _ in range(5)]
        sim = MonteCarloSimulator(trades)
        result = sim.run()
        assert "error" in result
        assert "Not enough trades" in result["error"]

    def test_probability_of_ruin_calculation(self):
        """Test probability of ruin calculation with guaranteed loss."""
        # Trades always lose 10%
        trades = [{'return_pct': -10.0} for _ in range(20)]
        sim = MonteCarloSimulator(trades, initial_capital=10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 100
            n_trades = 20
            # Always pick index 0 (loss)
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            mock_gen.choice.return_value = np.arange(5)

            # 10000 * (0.9)^20 = 1215.77
            # Initial = 10000. 50% drawdown = 5000.
            # Final 1215 < 5000. So ruin should be 100%

            result = sim.run(simulations=simulations, ruin_threshold_pct=0.5)

            # Check prob_ruin_50pct (key name might be prob_ruin_50pct based on code reading)
            # In code: "prob_ruin_50pct": round(prob_ruin, 2)
            assert result["prob_ruin_50pct"] == 100.0

    def test_custom_ruin_threshold_bug(self):
        """
        Test that custom ruin threshold is respected.
        Currently expected to fail if the bug exists.
        """
        # Trades lose 1% each time. 20 trades.
        # Final equity = 10000 * (0.99)^20 = 8179.
        # Drawdown is approx (10000 - 8179)/10000 = 18.2%
        # If ruin_threshold is 0.10 (10%), this should be ruin.
        # If ruin_threshold is 0.50 (50%), this is NOT ruin.

        trades = [{'return_pct': -1.0} for _ in range(20)]
        sim = MonteCarloSimulator(trades, initial_capital=10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 100
            n_trades = 20
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            mock_gen.choice.return_value = np.arange(5)

            # Run with 10% threshold.
            # Since drawdown is ~18%, it > 10%, so ruin should be 100%.
            # However, if code hardcodes 0.50, it will check if 18% > 50% (False), so ruin 0%.
            result = sim.run(simulations=simulations, ruin_threshold_pct=0.10)

            # This assertion will fail if the bug exists (it will return 0.0 instead of 100.0)
            assert result["prob_ruin_50pct"] == 100.0

class TestSimpleMonteCarlo:
    def test_simple_monte_carlo_success(self):
        """Test run_simple_monte_carlo with mock strategies."""
        # Mock strategy objects with .net_pnl
        strategies = [MagicMock(net_pnl=100.0) for _ in range(20)]

        with patch('numpy.random.choice') as mock_choice:
            # Deterministic choice: always return 100.0
            # shape=(num_sims, forecast_trades)
            num_sims = 100
            forecast_trades = 10
            mock_choice.return_value = np.full((num_sims, forecast_trades), 100.0)

            result = run_simple_monte_carlo(strategies, start_equity=10000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            assert "error" not in result
            # Expected profit: 10 trades * 100 = 1000
            assert result["expected_profit"] == 1000.0
            assert result["median_equity"] == 11000.0
            assert result["risk_of_ruin_50pct"] == 0.0

    def test_simple_monte_carlo_ruin(self):
        """Test risk of ruin in simple monte carlo."""
        # Strategies with -1000 loss
        strategies = [MagicMock(net_pnl=-1000.0) for _ in range(20)]

        with patch('numpy.random.choice') as mock_choice:
            num_sims = 100
            forecast_trades = 6
            # 6 trades * -1000 = -6000.
            # Start 10000. End 4000.
            # Drawdown > 50% (threshold defaults to 0.5)
            # Wait, threshold is 0.5 * 10000 = 5000.
            # 4000 < 5000. So Ruin.

            mock_choice.return_value = np.full((num_sims, forecast_trades), -1000.0)

            result = run_simple_monte_carlo(strategies, start_equity=10000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            assert result["risk_of_ruin_50pct"] == 100.0
