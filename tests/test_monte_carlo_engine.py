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
            # Note: run() calls integers with size=(simulations, n_trades)
            # The code actually uses self.returns_pct so n_trades is len(returns_pct)
            # Here n_trades = 20.
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

    def test_run_boundary_trades(self):
        """Test boundary condition for minimum trades (9 vs 10)."""
        # 9 trades - should fail
        trades_9 = [{'return_pct': 5.0} for _ in range(9)]
        sim_9 = MonteCarloSimulator(trades_9)
        res_9 = sim_9.run()
        assert "error" in res_9
        assert "Not enough trades" in res_9["error"]

        # 10 trades - should succeed
        trades_10 = [{'return_pct': 5.0} for _ in range(10)]
        sim_10 = MonteCarloSimulator(trades_10)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen
            # Mock integers
            mock_gen.integers.return_value = np.zeros((10, 10), dtype=int)
            # Mock choice
            mock_gen.choice.return_value = np.arange(5)

            res_10 = sim_10.run(simulations=10)
            assert "error" not in res_10
            assert res_10["simulations"] == 10

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
            result = sim.run(simulations=simulations, ruin_threshold_pct=0.10)
            assert result["prob_ruin_50pct"] == 100.0

    def test_run_monte_carlo_percentiles(self):
        """Test percentile calculations with deterministic outcomes."""
        # 5 distinct trades: -10%, -5%, 0%, 5%, 10%
        # We need at least 10 trades to avoid error, so we duplicate them
        trades = [
            {'return_pct': -10.0}, {'return_pct': -10.0},
            {'return_pct': -5.0}, {'return_pct': -5.0},
            {'return_pct': 0.0}, {'return_pct': 0.0},
            {'return_pct': 5.0}, {'return_pct': 5.0},
            {'return_pct': 10.0}, {'return_pct': 10.0}
        ]
        # Total 10 trades.
        # Indices 0-1 are -10%
        # Indices 2-3 are -5%
        # Indices 4-5 are 0%
        # Indices 6-7 are 5%
        # Indices 8-9 are 10%

        sim = MonteCarloSimulator(trades, initial_capital=10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 5
            # We want to force each simulation to pick a specific return type.
            # But the 'run' method generates indices (simulations, n_trades).
            # The code does:
            # returns_decimal = np.array(self.returns_pct) / 100.0
            # random_indices = rng.integers(0, n_trades, size=(simulations, n_trades))
            # sim_returns = returns_decimal[random_indices]
            #
            # The number of steps in simulation is n_trades (10 in this case).
            #
            # We want Sim 0 to have all -10% (indices 0)
            # We want Sim 1 to have all -5% (indices 2)
            # We want Sim 2 to have all 0% (indices 4)
            # We want Sim 3 to have all 5% (indices 6)
            # We want Sim 4 to have all 10% (indices 8)

            n_trades = 10 # From our list above
            indices = np.zeros((simulations, n_trades), dtype=int)

            indices[0, :] = 0 # -10%
            indices[1, :] = 2 # -5%
            indices[2, :] = 4 # 0%
            indices[3, :] = 6 # 5%
            indices[4, :] = 8 # 10%

            mock_gen.integers.return_value = indices

            # Mock choice for sample curves (return all 5)
            mock_gen.choice.return_value = np.arange(simulations)

            result = sim.run(simulations=simulations)

            # Expected Final Equities (after 10 steps)
            # Sim 0: 10000 * 0.9^10
            # Sim 1: 10000 * 0.95^10
            # Sim 2: 10000 * 1.0^10
            # Sim 3: 10000 * 1.05^10
            # Sim 4: 10000 * 1.1^10

            finals = [
                10000.0 * (0.9 ** 10),
                10000.0 * (0.95 ** 10),
                10000.0 * (1.0 ** 10),
                10000.0 * (1.05 ** 10),
                10000.0 * (1.1 ** 10)
            ]

            # Percentiles (p5, p25, p50, p75, p95) of these 5 values
            expected_p5 = np.percentile(finals, 5)
            expected_p50 = np.percentile(finals, 50)
            expected_p95 = np.percentile(finals, 95)

            # Check equity_curve_percentiles final values
            # The result['equity_curve_percentiles'] contains lists.
            # The last element of each list corresponds to the final equity.

            p5_list = result["equity_curve_percentiles"]["p5"]
            p50_list = result["equity_curve_percentiles"]["p50"]
            p95_list = result["equity_curve_percentiles"]["p95"]

            assert p5_list[-1] == pytest.approx(expected_p5, rel=1e-2)
            assert p50_list[-1] == pytest.approx(expected_p50, rel=1e-2)
            assert p95_list[-1] == pytest.approx(expected_p95, rel=1e-2)

    def test_run_monte_carlo_ruin_threshold_logic(self):
        """Test ruin threshold logic with different thresholds for same drawdown."""
        # Single trade type: -20% return.
        trades = [{'return_pct': -20.0}] * 10 # Need >= 10 trades
        sim = MonteCarloSimulator(trades, initial_capital=10000.0)

        with patch('numpy.random.default_rng') as mock_rng:
            mock_gen = MagicMock()
            mock_rng.return_value = mock_gen

            simulations = 10
            n_trades = 10

            # All simulations pick index 0 (loss)
            # So every step is a 20% loss.
            # Step 1: 8000. Drawdown (10000-8000)/10000 = 20%.
            # Subsequent steps will have deeper drawdowns relative to initial peak 10000?
            # MonteCarloSimulator drawdown calculation:
            # running_max = np.maximum.accumulate(equity_curves, axis=1)
            # drawdowns = (equity_curves / running_max) - 1.0
            #
            # Curve: 10000, 8000, 6400, ...
            # Max: 10000, 10000, 10000...
            # DD: 0, -0.2, -0.36...
            #
            # The max drawdown will be at the end (largest negative number).
            # We want to verify that if max_dd is say 20%, threshold logic works.
            # But here max_dd will be huge (close to 100% loss after 10 steps).
            # We want to limit the steps or control the outcome precisely so max_dd is exactly 20%.

            # To get exactly 20% max DD, we can have 1 step of -20%, then flat or up.
            # But the simulation runs for n_trades steps (10).
            # If we want to test threshold logic, we can just let it be huge drawdown,
            # and test thresholds that are smaller or larger than that huge drawdown.

            # Alternatively, we use trades that have 0 return except one.
            # But we can't easily control the sequence with just rng.integers unless we mock the sequence precisely.

            # Let's stick to the huge drawdown case.
            # After 1 step: 8000. DD = 20%.
            # Max DD will be AT LEAST 20%.
            # So if we set threshold to 15%, it MUST be ruin.
            # If we set threshold to 99% (0.99), it might not be ruin if steps are few?
            # 0.8^10 is ~0.10. Equity ~1000. DD ~90%.
            # So threshold 0.95 (95%) might still be safe.

            mock_gen.integers.return_value = np.zeros((simulations, n_trades), dtype=int)
            mock_gen.choice.return_value = np.arange(simulations) # any valid choice

            # Case 1: Threshold 15% (0.15). Drawdown > 20% > 15%. Ruin = 100%.
            res1 = sim.run(simulations=simulations, ruin_threshold_pct=0.15)
            assert res1["prob_ruin_50pct"] == 100.0

            # Case 2: Threshold 95% (0.95).
            # 0.8^10 = 0.107. Drawdown = (10000 - 1073)/10000 = ~89.2%
            # 89.2% < 95%. So Ruin = 0%.
            res2 = sim.run(simulations=simulations, ruin_threshold_pct=0.95)
            assert res2["prob_ruin_50pct"] == 0.0

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

    def test_simple_monte_carlo_dict_input(self):
        """Test simple monte carlo with dictionary inputs."""
        strategies = [{'pnl': 50.0}, {'pnl': -50.0}] * 10 # ensure > 10

        with patch('numpy.random.choice') as mock_choice:
            num_sims = 10
            forecast_trades = 5

            # Force choice to always pick 50.0
            mock_choice.return_value = np.full((num_sims, forecast_trades), 50.0)

            result = run_simple_monte_carlo(strategies, start_equity=1000.0, num_sims=num_sims, forecast_trades=forecast_trades)

            # 5 * 50 = 250 profit. End equity 1250.
            assert result["expected_profit"] == 250.0
            assert result["median_equity"] == 1250.0

    def test_simple_monte_carlo_mixed_input(self):
        """Test simple monte carlo with mixed dict and object inputs."""
        s1 = {'pnl': 100.0}
        s2 = MagicMock(net_pnl=100.0)
        strategies = [s1, s2] * 10

        with patch('numpy.random.choice') as mock_choice:
             # Force choice to always pick 100.0
             mock_choice.return_value = np.full((10, 5), 100.0)

             result = run_simple_monte_carlo(strategies, start_equity=1000.0, num_sims=10, forecast_trades=5)

             assert result["expected_profit"] == 500.0

    def test_simple_monte_carlo_missing_keys(self):
        """Test simple monte carlo with missing keys in dict (default 0.0)."""
        strategies = [{'other': 100.0}] * 10

        with patch('numpy.random.choice') as mock_choice:
             # Since input pnls will be [0.0, 0.0, ...], choice will pick 0.0
             mock_choice.return_value = np.zeros((10, 5))

             result = run_simple_monte_carlo(strategies, start_equity=1000.0, num_sims=10, forecast_trades=5)

             assert result["expected_profit"] == 0.0
