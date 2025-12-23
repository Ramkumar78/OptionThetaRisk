import numpy as np
import pandas as pd
from scipy.signal import hilbert
from scipy.stats import entropy

class QuantPhysicsEngine:
    @staticmethod
    def calculate_hurst(series):
        """
        Calculates the Hurst Exponent of a time series.
        H < 0.5: Mean Reverting
        H = 0.5: Random Walk
        H > 0.5: Trending
        """
        try:
            ts = series.values
            if len(ts) < 100:
                return 0.5

            # Generalized Hurst Exponent (GHE) using Second Moment (RMS)
            # We use RMS because standard deviation centers the data (removes trend),
            # whereas RMS captures the drift/trend magnitude.

            lags = range(2, 20)

            # Calculate RMS of lagged differences
            # <|y(t+tau) - y(t)|^2> ~ tau^(2H)
            # sqrt(<...>) ~ tau^H

            tau_values = []
            for lag in lags:
                diff = np.subtract(ts[lag:], ts[:-lag])
                rms = np.sqrt(np.mean(diff**2))
                tau_values.append(rms)

            # Use a linear fit to estimate the Hurst Exponent
            # log(rms) ~ H * log(lag)
            poly = np.polyfit(np.log(lags), np.log(tau_values), 1)

            h = poly[0]

            # Clamp to 0-1 range to avoid wild values
            return max(0.0, min(1.0, h))
        except Exception:
            return 0.5

    @staticmethod
    def shannon_entropy(series):
        """Calculates Shannon Entropy of the price distribution."""
        try:
            # Normalize to probability distribution
            # Use returns or differenced data to be stationary
            diff = series.diff().dropna()
            if len(diff) == 0: return 1.0

            counts, _ = np.histogram(diff, bins=20, density=True)
            # Remove zeros
            counts = counts[counts > 0]
            # Normalize
            prob = counts / np.sum(counts)
            return entropy(prob)
        except Exception:
            return 1.0

    @staticmethod
    def kalman_filter(series):
        """Applies a simple 1D Kalman Filter to smooth the series."""
        try:
            n_iter = len(series)
            sz = (n_iter,) # size of array
            xhat = np.zeros(sz)      # a posteri estimate of x
            P = np.zeros(sz)         # a posteri error estimate
            xhatminus = np.zeros(sz) # a priori estimate of x
            Pminus = np.zeros(sz)    # a priori error estimate
            K = np.zeros(sz)         # gain or blending factor

            Q = 1e-5 # process variance
            R = 0.01**2 # estimate of measurement variance

            # intial guesses
            xhat[0] = series.iloc[0]
            P[0] = 1.0

            for k in range(1, n_iter):
                # time update
                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q

                # measurement update
                K[k] = Pminus[k]/( Pminus[k]+R )
                xhat[k] = xhatminus[k]+K[k]*(series.iloc[k]-xhatminus[k])
                P[k] = (1-K[k])*Pminus[k]

            return pd.Series(xhat, index=series.index)
        except Exception:
            return series

    @staticmethod
    def instantaneous_phase(series):
        """Calculates instantaneous phase using Hilbert Transform."""
        try:
            # Detrend first (remove rolling mean)
            detrended = series - series.rolling(window=20).mean()
            detrended = detrended.fillna(0)

            if len(detrended) == 0: return 0.0

            analytic_signal = hilbert(detrended.values)
            phase = np.angle(analytic_signal)

            # Return last phase value
            return phase[-1]
        except Exception:
            return 0.0

    @staticmethod
    def generate_human_verdict(hurst, entropy, slope, price):
        """
        Centralized logic for Quantum Verdicts.
        Used by both Screener and Dashboard.
        """
        verdict = "WAIT"
        rationale = "No edge."

        if hurst is None: return "ERR", "No Data"

        # --- THE "REAL WORLD" THRESHOLDS (UPDATED) ---
        # Fixed: Raised thresholds to reduce false positives
        # Old: > 0.62 (Strong), > 0.55 (Moderate)
        # New: > 0.70 (Strong), > 0.60 (Moderate)

        trend_strength = "Weak"
        if hurst > 0.70: trend_strength = "🔥 Strong"
        elif hurst > 0.60: trend_strength = "✅ Moderate"

        noise_level = "Noisy"
        if entropy < 0.6: noise_level = "💎 Crystal Clear"
        elif entropy < 0.85: noise_level = "🌊 Tradeable"

        # LOGIC TREE
        # Fixed: Stricter Hurst requirement (0.60) for entry
        if hurst > 0.60 and entropy < 0.85:
            if slope > 0:
                verdict = f"BUY ({trend_strength})"
                rationale = f"Trend detected (H={hurst:.2f}) with acceptable noise."
            elif slope < 0:
                verdict = f"SHORT ({trend_strength})"
                rationale = f"Clean breakdown (H={hurst:.2f})."

        elif hurst < 0.45:
            verdict = "REVERSAL"
            rationale = f"Mean Reverting (H={hurst:.2f}). Fade moves."

        elif entropy > 0.9:
            verdict = "CHOP"
            rationale = "Market is too chaotic."

        else:
            verdict = "NEUTRAL"
            rationale = "Random Walk zone."

        return verdict, rationale
