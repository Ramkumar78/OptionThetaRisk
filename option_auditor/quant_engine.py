import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend

class QuantPhysicsEngine:
    """
    Advanced Mathematical & Physics-based Analysis Engine.
    Corrected for Log-Space R/S Analysis.
    """

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Calculates the Hurst Exponent using Log-Price differences.
        Robust against volatility spikes and flat lines.
        """
        try:
            # 1. Use Log Prices (Critical for Geometric Brownian Motion)
            # Handle non-positive values gracefully if they appear
            if (series <= 0).any():
                # fallback to raw series if log is impossible, or shift
                log_price = series
            else:
                log_price = np.log(series)

            lags = range(2, max_lag)
            tau = []

            for lag in lags:
                # Difference between Price(t+lag) and Price(t)
                diff = log_price.diff(lag).dropna()

                # Standard Deviation of differences
                std = np.std(diff)

                # Handle zero std (constant price) to avoid log(0)
                if std == 0:
                    std = 1e-9

                tau.append(std)

            # 3. Linear Fit on Log-Log scale
            # log(std) = H * log(lag) + C
            # Handle potential zeros in tau just in case
            tau_array = np.array(tau)
            tau_array[tau_array <= 0] = 1e-9

            m = np.polyfit(np.log(lags), np.log(tau_array), 1)

            hurst = m[0] # The slope IS the Hurst exponent.

            # Clamp result to 0-1 range
            return max(0.0, min(1.0, hurst))

        except Exception:
            return 0.5 # Default to Random Walk on error

    @staticmethod
    def shannon_entropy(series: pd.Series, base=2) -> float:
        try:
            data = series.pct_change().dropna()
            if len(data) < 10: return 1.0

            # Dynamic binning based on Rice Rule
            num_bins = int(2 * (len(data) ** (1/3)))
            # Ensure at least 5 bins
            num_bins = max(5, num_bins)

            hist, bin_edges = np.histogram(data, bins=num_bins, density=True)

            probs = hist * np.diff(bin_edges)
            probs = probs[probs > 0]

            entropy = -np.sum(probs * np.log(probs)) / np.log(base)
            return float(entropy)
        except:
            return 1.0

    @staticmethod
    def kalman_filter(series: pd.Series) -> pd.Series:
        try:
            x = series.values
            n_iter = len(x)
            sz = (n_iter,)

            # Rolling volatility for Dynamic R
            # Handle short series
            if len(series) < 30:
                returns_std = np.full(n_iter, 0.01)
            else:
                returns_std = series.pct_change().rolling(30).std().fillna(0.01).values

            Q = 1e-5
            xhat = np.zeros(sz)
            P = np.zeros(sz)
            xhatminus = np.zeros(sz)
            Pminus = np.zeros(sz)
            K = np.zeros(sz)

            xhat[0] = x[0]
            P[0] = 1.0

            for k in range(1, n_iter):
                # Dynamic R: High vol = trust measurement less (High R)
                # Ensure returns_std index access is safe
                vol_val = returns_std[k] if k < len(returns_std) else 0.01
                if np.isnan(vol_val): vol_val = 0.01

                vol_factor = (vol_val * x[k])
                R_dynamic = vol_factor ** 2
                if R_dynamic == 0: R_dynamic = 0.01

                # Predict
                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q

                # Update
                K[k] = Pminus[k] / (Pminus[k] + R_dynamic)
                xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
                P[k] = (1 - K[k]) * Pminus[k]

            return pd.Series(xhat, index=series.index)
        except Exception:
            return series

    @staticmethod
    def instantaneous_phase(series: pd.Series):
        """
        DSP: Hilbert Transform with Linear Detrending (No Lag).
        """
        try:
            # Linear detrending preserves the phase better than moving average subtraction
            price = series.values
            if len(price) < 10: return 0.0

            detrended = detrend(price, type='linear')

            analytic_signal = hilbert(detrended)
            instantaneous_phase = np.unwrap(np.angle(analytic_signal))
            return instantaneous_phase[-1]
        except:
            return 0.0
