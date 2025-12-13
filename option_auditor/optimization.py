import pandas as pd
import numpy as np
import yfinance as yf
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    def __init__(self, tickers: list, risk_free_rate: float = 0.045):
        self.tickers = list(set(tickers)) # deduplicate
        self.risk_free_rate = risk_free_rate
        self.returns_df = None
        self.cov_matrix = None
        self.mean_returns = None

    def set_data(self, df):
        """Use already downloaded data to avoid API calls."""
        if df is None or df.empty:
            return

        try:
            self._process_data(df)
        except Exception as e:
            logger.error(f"Error setting data in PortfolioOptimizer: {e}")

    def fetch_data(self, period="1y"):
        """Fetches historical data to calculate covariance and returns."""
        if not self.tickers:
            return

        try:
            # Fetch data
            # Use 'threads=True' for parallel download
            data = yf.download(self.tickers, period=period, interval="1d", group_by='ticker', progress=False, auto_adjust=True, threads=True)
            self._process_data(data)
        except Exception as e:
            logger.error(f"Error in PortfolioOptimizer.fetch_data: {e}")

    def _process_data(self, data):
        """Internal helper to process downloaded data into returns matrix."""
        try:
            # Extract closes
            close_prices = pd.DataFrame()

            for ticker in self.tickers:
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker in data.columns.levels[0]:
                        # Handle potential multi-level (Ticker, Price) or just Ticker[Close]
                        if 'Close' in data[ticker].columns:
                             series = data[ticker]['Close']
                             close_prices[ticker] = series
                        # Fallback if structure is different
                else:
                    # Single ticker or flat structure case
                    if ticker in data.columns:
                         close_prices[ticker] = data[ticker]
                    elif "Close" in data.columns and len(self.tickers) == 1:
                         # Case where single ticker download returns just OHLC columns
                         close_prices[self.tickers[0]] = data['Close']

            if close_prices.empty:
                logger.warning("PortfolioOptimizer: No price data extracted.")
                return

            # Calculate Daily Returns
            self.returns_df = close_prices.pct_change().dropna()

            if self.returns_df.empty:
                logger.warning("PortfolioOptimizer: Returns DataFrame is empty after dropna.")
                return

            # Covariance Matrix (Annualized)
            self.cov_matrix = self.returns_df.cov() * 252

            # Mean Returns (Annualized) - Simple historical mean as fallback
            self.mean_returns = self.returns_df.mean() * 252
        except Exception as e:
            logger.error(f"Error processing data in PortfolioOptimizer: {e}")

    def optimize_weights(self, expected_returns_map: dict = None, target_return: float = None) -> dict:
        """
        Performs Mean-Variance Optimization.

        Args:
            expected_returns_map: Dict {ticker: expected_annual_return_float}
                                  If provided, overrides historical mean returns.
            target_return: Minimum required return (constraint).
                           If None, maximizes Sharpe Ratio.

        Returns:
            Dict {ticker: weight} where weight is between 0.0 and 1.0
        """
        if self.cov_matrix is None or self.cov_matrix.empty:
            return {}

        # Ensure we only optimize for tickers we have data for
        valid_tickers = [t for t in self.cov_matrix.columns if t in self.tickers]
        if not valid_tickers:
            return {}

        num_assets = len(valid_tickers)

        # Prepare Expected Returns Vector
        mu = []
        for t in valid_tickers:
            if expected_returns_map and t in expected_returns_map:
                mu.append(expected_returns_map[t])
            else:
                # Fallback to historical mean if available, else 0
                val = self.mean_returns.get(t, 0.0) if self.mean_returns is not None else 0.0
                mu.append(val)

        mu = np.array(mu)
        sigma = self.cov_matrix.loc[valid_tickers, valid_tickers].values

        # Constraints
        # Sum of weights = 1
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

        # Target Return Constraint (if specified)
        if target_return is not None:
             constraints.append({'type': 'ineq', 'fun': lambda w: np.dot(w, mu) - target_return})

        # Bounds: 0 <= weight <= 1 (No short selling in this optimizer)
        bounds = tuple((0.0, 1.0) for _ in range(num_assets))

        # Initial Guess (Equal weights)
        init_guess = num_assets * [1. / num_assets,]

        # Optimization Function
        if target_return is not None:
             # Minimize Variance subject to Target Return
             def objective(w):
                 return np.dot(w.T, np.dot(sigma, w))
        else:
             # Maximize Sharpe Ratio (Minimize negative Sharpe)
             def objective(w):
                 p_ret = np.dot(w, mu)
                 p_vol = np.sqrt(np.dot(w.T, np.dot(sigma, w)))
                 if p_vol == 0: return 0
                 return - (p_ret - self.risk_free_rate) / p_vol

        try:
            result = minimize(objective, init_guess, method='SLSQP', bounds=bounds, constraints=constraints)

            # Even if result.success is False, we might have a result (e.g. iteration limit).
            # But usually we want success.
            # If optimization fails (e.g. target return infeasible), we might fallback to Max Sharpe.

            optimal_weights = result.x

            # Format output
            allocation = {}
            for i, t in enumerate(valid_tickers):
                weight = optimal_weights[i]
                if weight > 0.001: # Filter tiny weights
                    allocation[t] = round(weight, 4)

            # Check feasibility
            if target_return is not None and not result.success:
                 logger.warning(f"Optimization for target return {target_return} failed: {result.message}")

            return allocation

        except Exception as e:
            logger.error(f"Optimization calculation error: {e}")
            return {}
