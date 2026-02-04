import numpy as np
import logging

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
            "equity_curves": curves_data,
            "sample_equity_curves": sample_curves.tolist(),
            "message": f"Ran {simulations} simulations. {round(prob_ruin, 2)}% risk of >50% drawdown."
        }
