import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.monte_carlo_simulator import MonteCarloSimulator, run_simple_monte_carlo

class TestMonteCarloSimulator:
    def setup_method(self):
        self.trades_growth = [{'return_pct': 5.0} for _ in range(20)]
        self.trades_ruin = [{'return_pct': -10.0} for _ in range(20)]
        self.initial_capital = 10000.0

    def test_initialization(self):
        """Test initialization and data extraction."""
        trades = [{'return_pct': 10.0}, {'return_pct': -5.0}, {'other': 1}]
        sim = MonteCarloSimulator(trades, initial_capital=5000.0)

        assert sim.initial_capital == 5000.0
        # Should extract valid return_pct values
        assert len(sim.returns_pct) == 2
        assert sim.returns_pct == [10.0, -5.0]

    def test_insufficient_data(self):
        """Test error handling for insufficient trades (<10)."""
        # Empty
        sim_empty = MonteCarloSimulator([])
        res_empty = sim_empty.run()
        assert "error" in res_empty
        assert "No trade returns" in res_empty["error"]

        # Less than 10
        sim_few = MonteCarloSimulator([{'return_pct': 1.0} for _ in range(9)])
        res_few = sim_few.run()
        assert "error" in res_few
        assert "Not enough trades" in res_few["error"]

    def test_run_growth_scenario(self):
        """Test growth scenario with mocked positive returns."""
        sim = MonteCarloSimulator(self.trades_growth, self.initial_capital)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 100
            n_trades = len(self.trades_growth)

            # Mock integers: always pick index 0 (return 5.0%)
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            # Mock choice for sample curves
            mock_gen.choice.return_value = np.arange(5)

            result = sim.run(simulations=simulations)

            assert "error" not in result
            assert result["simulations"] == simulations

            # Calculate expected final equity: 10000 * (1.05)^20
            expected_final = 10000.0 * (1.05 ** 20)
            assert result["median_final_equity"] == pytest.approx(expected_final, rel=1e-2)

            # Drawdown should be 0.0 as it's monotonic growth
            assert result["median_drawdown"] == 0.0

            # Best and worst case should be identical in this deterministic test
            assert result["worst_case_return"] == pytest.approx(result["best_case_return"], rel=1e-2)

    def test_run_ruin_scenario(self):
        """Test ruin scenario with mocked negative returns."""
        sim = MonteCarloSimulator(self.trades_ruin, self.initial_capital)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 100
            n_trades = len(self.trades_ruin)

            # Mock integers: always pick index 0 (return -10.0%)
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            mock_gen.choice.return_value = np.arange(5)

            # Final equity: 10000 * (0.9)^20 ≈ 1215.77
            # Drawdown > 50% (threshold defaults to 0.5)
            # 1215 < 5000, so this is ruin.

            result = sim.run(simulations=simulations, ruin_threshold_pct=0.5)

            assert result["prob_ruin_50pct"] == 100.0
            assert result["median_drawdown"] < -50.0  # Should be around -87%

    def test_ruin_probability_calculation(self):
        """Test mixed ruin/growth scenario to verify probability calculation."""
        # Create trades with huge loss and huge gain options
        trades = [{'return_pct': -60.0}, {'return_pct': 100.0}] * 5 # 10 trades
        sim = MonteCarloSimulator(trades, self.initial_capital)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 10
            n_trades = 10

            # Create indices such that half simulations ruin, half grow
            # Sims 0-4: index 0 (-60%). One step is enough to ruin (>50% loss).
            # Sims 5-9: index 1 (+100%).
            indices = np.zeros((simulations, n_trades), dtype=int)
            indices[5:, :] = 1 # Set second half to use the winning trade

            mock_gen.integers.return_value = indices
            mock_gen.choice.return_value = np.arange(5)

            result = sim.run(simulations=simulations, ruin_threshold_pct=0.5)

            # 5 out of 10 ruined -> 50% probability
            assert result["prob_ruin_50pct"] == 50.0

    def test_ruin_boundary_condition(self):
        """Test boundary condition where drawdown equals threshold exactly."""
        # If we lose exactly 50%, is it ruin? Code uses < -threshold.
        # Drawdown is negative. So if DD = -0.5, and threshold = 0.5 (-0.5).
        # -0.5 < -0.5 is False. So NOT ruin.

        # We need a trade sequence that results in EXACTLY 50% loss at some point.
        # Trade 1: -50%.
        trades = [{'return_pct': -50.0}] * 10
        sim = MonteCarloSimulator(trades, 10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 10
            n_trades = 10
            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            mock_gen.choice.return_value = np.arange(5)

            # Run with threshold 0.5.
            # Step 1: 10000 -> 5000. DD = (5000/10000)-1 = -0.5.
            # Max DD will be <= -0.5.
            # Wait, subsequent steps reduce it further: 5000 -> 2500 (DD -0.75).
            # So max DD will be -0.75 or worse. That IS ruin.
            # We need to stop the bleeding to test the boundary.

            # Let's mock a scenario where it drops exactly 50% and stays there.
            # But the simulation loop runs for `n_trades` steps.
            # We can't control the loop logic itself, only the returns.
            # If returns are 0 after step 1, equity stays at 5000.

            # Mixed trades: -50% and 0%.
            trades_mixed = [{'return_pct': -50.0}, {'return_pct': 0.0}] * 5
            sim_mixed = MonteCarloSimulator(trades_mixed, 10000.0)

            # Construct indices: Step 0 use index 0 (-50%). Steps 1..9 use index 1 (0%).
            indices = np.ones((simulations, n_trades), dtype=int)
            indices[:, 0] = 0

            mock_gen.integers.return_value = indices
            mock_gen.choice.return_value = np.arange(5)

            # Result: Equity goes 10000 -> 5000 -> 5000...
            # Max DD = -0.5.
            # -0.5 < -0.5 is False. Ruin should be 0%.
            result = sim_mixed.run(simulations=simulations, ruin_threshold_pct=0.5)
            assert result["prob_ruin_50pct"] == 0.0

            # Now test with threshold 0.49 (49%). -0.5 < -0.49 is True. Ruin should be 100%.
            result_strict = sim_mixed.run(simulations=simulations, ruin_threshold_pct=0.49)
            assert result_strict["prob_ruin_50pct"] == 100.0

    def test_massive_loss_handling(self):
        """Test handling of massive losses (-99%, -100%)."""
        trades = [{'return_pct': -100.0}] * 10
        sim = MonteCarloSimulator(trades, 10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            # All -100%
            mock_gen.integers.return_value = np.zeros((10, 10), dtype=int)
            mock_gen.choice.return_value = np.arange(5)

            # 10000 -> 0.
            result = sim.run(simulations=10)

            # Should not crash.
            assert result["median_final_equity"] == 0.0
            assert result["prob_ruin_50pct"] == 100.0
            assert result["worst_case_return"] == -100.0


class TestSimpleMonteCarlo:
    def test_insufficient_strategies(self):
        """Test error when fewer than 10 strategies provided."""
        strategies = [{'pnl': 100.0}] * 5
        res = run_simple_monte_carlo(strategies, 10000.0)
        assert "error" in res
        assert "at least 10 trades" in res["error"]

    def test_strategy_input_types(self):
        """Test both dictionary and object inputs."""
        class StrategyObj:
            def __init__(self, pnl):
                self.net_pnl = pnl

        strategies = [
            {'pnl': 50.0},
            StrategyObj(50.0)
        ] * 5 # Total 10

        with patch('numpy.random.choice') as mock_choice:
            num_sims = 10
            forecast_trades = 5
            # Force choice to always pick 50.0
            mock_choice.return_value = np.full((num_sims, forecast_trades), 50.0)

            result = run_simple_monte_carlo(strategies, 1000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            # 5 trades * 50 = 250.
            assert result["expected_profit"] == 250.0
            assert result["median_equity"] == 1250.0

    def test_growth_logic(self):
        """Test simple MC growth logic."""
        strategies = [{'pnl': 100.0}] * 10

        with patch('numpy.random.choice') as mock_choice:
            num_sims = 100
            forecast_trades = 10
            mock_choice.return_value = np.full((num_sims, forecast_trades), 100.0)

            result = run_simple_monte_carlo(strategies, 10000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            assert result["risk_of_ruin_50pct"] == 0.0
            assert result["median_equity"] == 11000.0

    def test_ruin_logic(self):
        """Test simple MC ruin logic."""
        strategies = [{'pnl': -2000.0}] * 10

        with patch('numpy.random.choice') as mock_choice:
            num_sims = 100
            forecast_trades = 5
            # 5 * -2000 = -10000. Equity goes 10000 -> 0.
            mock_choice.return_value = np.full((num_sims, forecast_trades), -2000.0)

            result = run_simple_monte_carlo(strategies, 10000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            # Ruin threshold is 5000 (default 50%). 0 < 5000.
            assert result["risk_of_ruin_50pct"] == 100.0

    def test_missing_pnl_key(self):
        """Test fallback to 0.0 for missing keys."""
        strategies = [{'other': 123}] * 10

        with patch('numpy.random.choice') as mock_choice:
            # PnLs extracted will be 0.0
            # choice will pick from [0.0, 0.0...]
            mock_choice.return_value = np.zeros((10, 5))

            result = run_simple_monte_carlo(strategies, 1000.0, num_sims=10, forecast_trades=5)

            assert result["expected_profit"] == 0.0
            assert result["median_equity"] == 1000.0
