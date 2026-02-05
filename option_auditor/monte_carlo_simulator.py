import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger("MonteCarloSimulator")

class MonteCarloSimulator:
    def __init__(self, trades: list, initial_capital: float = 10000.0):
        """
        :param trades: List of dicts, each containing 'return_pct'.
        :param initial_capital: Starting equity for simulations.
        """
        self.trades = trades
        self.initial_capital = initial_capital
        # Extract percentage returns (e.g., 5.0 for 5%)
        self.returns_pct = [t.get('return_pct', 0.0) for t in trades if t.get('return_pct') is not None]

    def run(self, simulations: int = 10000):
        if not self.returns_pct:
            return {"error": "No trade returns to simulate."}

        n_trades = len(self.returns_pct)
        if n_trades < 10:
             return {"error": "Not enough trades for meaningful Monte Carlo (min 10)."}

        # Convert to decimal returns for calculation (e.g., 0.05)
        returns_decimal = np.array(self.returns_pct) / 100.0

        final_equities = []
        max_drawdowns = []
        ruin_count = 0

        # Run Simulations
        # Vectorized approach might be complex with path dependence (drawdown),
        # so we'll use a loop for now, optimizing where possible.

        # We can pre-generate all random indices at once
        # Shape: (simulations, n_trades)
        rng = np.random.default_rng()
        random_indices = rng.integers(0, n_trades, size=(simulations, n_trades))

        # Select returns: (simulations, n_trades)
        sim_returns = returns_decimal[random_indices]

        # Calculate Equity Curves
        # Start with 1.0 (relative), then multiply by (1 + r)
        # cumulative product along axis 1
        equity_curves = np.cumprod(1 + sim_returns, axis=1) * self.initial_capital

        # Prepend initial capital to each curve for correct drawdown calc
        # shape becomes (simulations, n_trades + 1)
        start_caps = np.full((simulations, 1), self.initial_capital)
        equity_curves = np.hstack((start_caps, equity_curves))

        # Final Equities
        final_equities = equity_curves[:, -1]

        # Calculate Percentiles of Equity Curves
        # Axis 0 is simulations, Axis 1 is steps
        percentiles = [5, 25, 50, 75, 95]
        equity_quantiles = np.percentile(equity_curves, percentiles, axis=0)
        curve_percentiles = np.percentile(equity_curves, percentiles, axis=0)

        # Sample Curves
        # If simulations > 5, take 5 random. Else take all.
        n_samples = min(simulations, 5)
        sample_indices = rng.choice(simulations, n_samples, replace=False)
        sample_curves = equity_curves[sample_indices]

        # Max Drawdown Calculation
        # Running Max
        running_max = np.maximum.accumulate(equity_curves, axis=1)
        # Drawdown at each point
        drawdowns = (equity_curves - running_max) / running_max
        # Max Drawdown for each simulation (min value since drawdowns are negative or 0)
        max_dds = np.min(drawdowns, axis=1) # e.g., -0.20 for 20% DD

        # Risk of Ruin (Equity < 0 or DD > 50%? Usually Ruin is losing everything or hitting a hard stop)
        # Let's define Ruin as hitting < 50% of starting capital (severe) or 0
        # Common def: Ruin is blowing up account. Let's say < 0.
        # But in pure compounding, it never hits < 0 unless return is <= -100%.
        # If returns are simple PnL added, it can go < 0. Backtester uses simple compounding logic?
        # UnifiedBacktester: self.equity -= (shares * price); self.equity += proceeds.
        # It buys shares. If price goes to 0, you lose 100% of trade.
        # So return is -1. 1 + (-1) = 0. Equity becomes 0.

        # Let's define Ruin as > 50% Drawdown
        ruin_mask = max_dds < -0.50
        ruin_count = np.sum(ruin_mask)

        prob_ruin = (ruin_count / simulations) * 100.0

        # Stats
        median_return = np.median(final_equities)
        pct95_return = np.percentile(final_equities, 95)
        pct5_return = np.percentile(final_equities, 5) # Worst 5% case

        median_dd = np.median(max_dds) * 100 # Convert back to %
        pct95_dd = np.percentile(max_dds, 5) * 100 # 5th percentile is the "95% confidence worst case" (negative number)
        # e.g. if median is -10%, 5th percentile might be -30%.

        # Expected Return (CAGR-like? No just total return over the period)
        avg_final_equity = np.mean(final_equities)
        avg_return_pct = ((avg_final_equity - self.initial_capital) / self.initial_capital) * 100

        # Calculate Equity Curve Percentiles (Cone)
        # shape: (5, n_trades + 1)
        percentiles = [5, 25, 50, 75, 95]
        equity_quantiles = np.percentile(equity_curves, percentiles, axis=0)

        curves_data = {
            "p05": np.round(equity_quantiles[0], 2).tolist(),
            "p25": np.round(equity_quantiles[1], 2).tolist(),
            "p50": np.round(equity_quantiles[2], 2).tolist(),
            "p75": np.round(equity_quantiles[3], 2).tolist(),
            "p95": np.round(equity_quantiles[4], 2).tolist(),
        }

        return {
            "simulations": simulations,
            "initial_capital": self.initial_capital,
            "prob_ruin_50pct": round(prob_ruin, 2), # % chance of 50% drawdown
            "median_final_equity": round(median_return, 2),
            "avg_return_pct": round(avg_return_pct, 2),
            "worst_case_return": round(((pct5_return - self.initial_capital)/self.initial_capital)*100, 2),
            "best_case_return": round(((pct95_return - self.initial_capital)/self.initial_capital)*100, 2),
            "median_drawdown": round(median_dd, 2),
            "worst_case_drawdown": round(pct95_dd, 2), # 95% Confidence Level Max Drawdown
            "equity_curve_percentiles": {
                "p5": curve_percentiles[0].tolist(),
                "p25": curve_percentiles[1].tolist(),
                "p50": curve_percentiles[2].tolist(),
                "p75": curve_percentiles[3].tolist(),
                "p95": curve_percentiles[4].tolist(),
            },
            "sample_equity_curves": sample_curves.tolist(),
            "equity_curves": curves_data,
            "message": f"Ran {simulations} simulations. {round(prob_ruin, 2)}% risk of >50% drawdown."
        }

def run_simple_monte_carlo(strategies: List[Any], start_equity: float, num_sims: int = 1000, forecast_trades: int = 50) -> Dict:
    """
    Runs a Monte Carlo simulation to project future portfolio performance.
    Returns: Probability of Ruin, Median Outcome, and 5th Percentile (Worst Case).
    """
    if not strategies or len(strategies) < 10:
        return {"error": "Need at least 10 trades for Monte Carlo"}

    # 1. Extract Trade Statistics
    # We use the actual PnL distribution, not just averages, to capture "fat tails" (outliers)
    pnls = [s.net_pnl for s in strategies]

    # 2. Run Simulations (Vectorized with NumPy for speed)
    # We simulate 'forecast_trades' into the future, 'num_sims' times.
    # We randomly sample from your HISTORICAL PnL list.
    # This assumes your future performance distribution matches your past.

    # Shape: (num_sims, forecast_trades)
    simulated_trades = np.random.choice(pnls, size=(num_sims, forecast_trades), replace=True)

    # Cumulative Sum to get Equity Curve
    # Axis 1 = across the trades in a single simulation
    sim_curves = np.cumsum(simulated_trades, axis=1) + start_equity

    # 3. Calculate Metrics

    # Ending Equity for all simulations
    ending_equities = sim_curves[:, -1]

    # Risk of Ruin (Probability that equity drops below 50% of start at ANY point)
    # Check if ANY point in the curve < start_equity * 0.5
    ruin_threshold = start_equity * 0.5
    min_equities = np.min(sim_curves, axis=1)
    ruin_count = np.sum(min_equities < ruin_threshold)
    risk_of_ruin_pct = (ruin_count / num_sims) * 100.0

    # Percentiles
    median_outcome = np.percentile(ending_equities, 50)
    worst_case_outcome = np.percentile(ending_equities, 5) # 5th percentile (95% confidence you won't do worse)
    best_case_outcome = np.percentile(ending_equities, 95)

    return {
        "simulations": num_sims,
        "forecast_trades": forecast_trades,
        "risk_of_ruin_50pct": round(float(risk_of_ruin_pct), 1),
        "median_equity": round(float(median_outcome), 2),
        "worst_case_equity": round(float(worst_case_outcome), 2),
        "best_case_equity": round(float(best_case_outcome), 2),
        "expected_profit": round(float(median_outcome - start_equity), 2)
    }
