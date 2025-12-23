import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend

class QuantPhysicsEngine:

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Standard Rescaled Range (R/S) Analysis.
        More sensitive to trends than Aggregated Variance.
        """
        try:
            # 1. Prepare Returns
            returns = np.log(series / series.shift(1)).dropna()
            if len(returns) < 50: return 0.5

            # 2. R/S Calculation Loop
            # We calculate the range of cumulative deviations relative to standard deviation
            lags = range(2, min(max_lag, len(returns) // 2))
            rs_values = []

            for lag in lags:
                # Split data into chunks of size 'lag'
                num_chunks = len(returns) // lag
                chunk_rs = []

                for i in range(num_chunks):
                    chunk = returns.iloc[i*lag : (i+1)*lag]

                    # Calculate Mean and Deviations
                    mean = chunk.mean()
                    cumsum_dev = (chunk - mean).cumsum()

                    # Range (R) and StdDev (S)
                    R = cumsum_dev.max() - cumsum_dev.min()
                    S = chunk.std(ddof=1)

                    if S > 0:
                        chunk_rs.append(R / S)

                if chunk_rs:
                    rs_values.append(np.mean(chunk_rs))

            # 3. Linear Regression: log(R/S) = H * log(lag) + C
            if not rs_values: return 0.5

            valid_indices = np.where(np.array(rs_values) > 0)
            if len(valid_indices[0]) < 2: return 0.5

            y = np.log(np.array(rs_values)[valid_indices])
            x = np.log(list(lags))[valid_indices]

            H, _ = np.polyfit(x, y, 1)

            # Cap result (Financial markets rarely exceed 0.8)
            return max(0.3, min(0.85, H))

        except Exception as e:
            # print(f"Hurst Error: {e}")
            return 0.5

    @staticmethod
    def shannon_entropy(series: pd.Series, base=2) -> float:
        """
        Normalized Shannon Entropy (0 to 1 scale).
        Makes interpretation consistent across tickers.
        """
        try:
            data = series.pct_change().dropna()
            if len(data) < 10: return 1.0

            # Binning
            num_bins = int(len(data) ** 0.5) # Square root choice
            counts, _ = np.histogram(data, bins=num_bins, density=False)

            probs = counts / np.sum(counts)
            probs = probs[probs > 0]

            # Raw Entropy
            S = -np.sum(probs * np.log(probs) / np.log(base))

            # Normalize by Max Entropy (log(num_bins))
            max_S = np.log(num_bins) / np.log(base)

            # Return inverted score: 0 = Chaos, 1 = Order (Optional, but let's stick to standard)
            # Standard: Low is Order.
            return S / max_S if max_S > 0 else 1.0
        except:
            return 1.0

    @staticmethod
    def kalman_filter(series: pd.Series) -> pd.Series:
        # (Keep the existing dynamic R version I gave you previously)
        try:
            x = series.values
            n_iter = len(x)
            sz = (n_iter,)
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
                vol_factor = (returns_std[k] * x[k]) if k < len(returns_std) else x[k]*0.01
                R_dynamic = vol_factor ** 2
                if R_dynamic == 0: R_dynamic = 0.01

                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q
                K[k] = Pminus[k] / (Pminus[k] + R_dynamic)
                xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
                P[k] = (1 - K[k]) * Pminus[k]

            return pd.Series(xhat, index=series.index)
        except:
            return series

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
