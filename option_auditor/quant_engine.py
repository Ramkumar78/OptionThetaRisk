import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend

class QuantPhysicsEngine:
    """
    Advanced Mathematical & Physics-based Analysis Engine.
    Optimized for Dynamic Volatility and Signal Fidelity.
    """

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Calculates the Hurst Exponent.
        H < 0.5: Mean Reverting
        H = 0.5: Random Walk
        H > 0.5: Trending
        """
        try:
            # Ensure strictly positive for log
            series = series[series > 0]
            if len(series) < max_lag: return 0.5

            lags = range(2, max_lag)

            # Use Log Prices to handle geometric scaling (GBM)
            log_prices = np.log(series.values)

            # Calculate RMS of differences at various lags
            # RMS(log_p(t+k) - log_p(t)) ~ k^H
            # RMS captures both trend (mean drift) and diffusion (variance)
            tau = []
            for lag in lags:
                diff = log_prices[lag:] - log_prices[:-lag]
                rms = np.sqrt(np.mean(diff**2))
                tau.append(rms)

            # Linear Fit: log(rms) vs log(lags)
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0]
        except:
            return 0.5

    @staticmethod
    def shannon_entropy(series: pd.Series, base=2) -> float:
        """
        Measures Market Disorder.
        """
        try:
            # Normalize price to returns to make it stationary
            data = series.pct_change().dropna()
            if len(data) < 10: return 1.0

            # Dynamic binning based on Rice Rule
            num_bins = int(2 * (len(data) ** (1/3)))
            hist, bin_edges = np.histogram(data, bins=num_bins, density=True)

            probs = hist * np.diff(bin_edges)
            probs = probs[probs > 0] # Avoid log(0)

            entropy = -np.sum(probs * np.log(probs)) / np.log(base)
            return entropy
        except:
            return 1.0

    @staticmethod
    def kalman_filter(series: pd.Series) -> pd.Series:
        """
        DYNAMIC KALMAN FILTER.
        Automatically tunes 'R' (Measurement Noise) based on the asset's volatility.
        """
        x = series.values
        n_iter = len(x)
        sz = (n_iter,)

        # 1. Calculate Dynamic Volatility (Measurement Noise R)
        # We use the variance of the last 30 days of returns to tune the filter
        # If the stock is wild, R increases (filter slows down to ignore noise)
        # If the stock is calm, R decreases (filter speeds up to catch moves)
        returns_std = series.pct_change().rolling(30).std().fillna(0.01).values

        # Baseline Process Noise (Q) - How fast we expect the "Truth" to change
        Q = 1e-5

        xhat = np.zeros(sz)
        P = np.zeros(sz)
        xhatminus = np.zeros(sz)
        Pminus = np.zeros(sz)
        K = np.zeros(sz)

        xhat[0] = x[0]
        P[0] = 1.0

        for k in range(1, n_iter):
            # Dynamic R based on recent volatility at step k
            # Scaling factor: Volatility^2
            R_dynamic = (returns_std[k] * x[k]) ** 2 if k < len(returns_std) else 1.0
            if R_dynamic == 0: R_dynamic = 0.01

            # Time Update
            xhatminus[k] = xhat[k-1]
            Pminus[k] = P[k-1] + Q

            # Measurement Update
            K[k] = Pminus[k] / (Pminus[k] + R_dynamic)
            xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
            P[k] = (1 - K[k]) * Pminus[k]

        return pd.Series(xhat, index=series.index)

    @staticmethod
    def instantaneous_phase(series: pd.Series):
        """
        DSP: Hilbert Transform with Linear Detrending (No Lag).
        """
        try:
            # Linear detrending preserves the phase better than moving average subtraction
            price = series.values
            detrended = detrend(price, type='linear')

            analytic_signal = hilbert(detrended)
            instantaneous_phase = np.unwrap(np.angle(analytic_signal))
            return instantaneous_phase[-1]
        except:
            return 0.0
