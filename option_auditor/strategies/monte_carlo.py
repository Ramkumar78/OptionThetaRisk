import numpy as np
import pandas as pd
import yfinance as yf

def screen_monte_carlo_forecast(ticker: str, days: int = 30, sims: int = 1000):
    """
    Project stock price 30 days out using Monte Carlo with Historical Bootstrapping.
    FIX: Replaces Gaussian GBM with Bootstrapping to capture Fat Tails.
    """
    try:
        # Fetch sufficient history to capture tail events (2 years minimum)
        df = yf.download(ticker, period="2y", progress=False)
        if df.empty or len(df) < 100: return None

        if isinstance(df.columns, pd.MultiIndex):
            try:
                if ticker in df.columns.levels[0]:
                    df = df[ticker].copy()
                else:
                    df.columns = df.columns.get_level_values(0)
            except: pass

        # Calculate Log Returns
        log_returns = np.log(df['Close'] / df['Close'].shift(1)).dropna()
        if log_returns.empty: return None

        last_price = float(df['Close'].iloc[-1])

        # BOOTSTRAPPING: Sample from ACTUAL past returns with replacement.
        # This preserves skewness and kurtosis (fat tails).
        random_returns = np.random.choice(log_returns, size=(days, sims), replace=True)

        # Reconstruct Price Paths
        # Cumulative sum of log returns -> cumulative product of price
        price_paths = last_price * np.exp(np.cumsum(random_returns, axis=0))

        final_prices = price_paths[-1]

        # Probability of Drop > 10%
        # Measures how many simulation paths ended below 90% of current price
        prob_drop_10pct = np.mean(final_prices < (last_price * 0.90)) * 100

        median_forecast = np.median(final_prices)

        # Annualized Volatility for context
        vol_annual = log_returns.std() * np.sqrt(252)

        return {
            "ticker": ticker,
            "current": last_price,
            "median_forecast": median_forecast,
            "prob_drop_10pct": f"{prob_drop_10pct:.1f}%",
            "volatility_annual": f"{vol_annual * 100:.1f}%",
            "method": "Historical Bootstrapping (Fat Tails)"
        }
    except Exception:
        return None
