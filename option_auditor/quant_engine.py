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
            # Check if input is valid
            if series.empty: return None

            returns = np.log(series / series.shift(1)).dropna()
            if len(returns) < 50: return None # FIX: Return None, not 0.5

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
            if not rs_values: return None

            valid_indices = np.where(np.array(rs_values) > 0)
            if len(valid_indices[0]) < 2: return None

            y = np.log(np.array(rs_values)[valid_indices])
            x = np.log(list(lags))[valid_indices]

            H, _ = np.polyfit(x, y, 1)

            # Cap result (Financial markets rarely exceed 0.8)
            return max(0.3, min(0.85, H))

        except Exception as e:
            # print(f"Hurst Error: {e}")
            return None

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
        """
        Fixed Kalman Filter using Log Prices to avoid Scale Bias.
        Price level independent.
        """
        try:
            # FIX: Use Log Prices
            # If we process raw prices, the noise R scales with Price^2,
            # while Q is constant, causing high priced stocks to lag.
            # Using log prices makes volatility (R) percentage based and consistent.

            if (series <= 0).any():
                # Fallback for negative/zero prices (shouldn't happen for stocks usually)
                return series

            x = np.log(series.values)
            n_iter = len(x)
            sz = (n_iter,)

            # Volatility of Returns (approx log diff)
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
                # R depends on current volatility of returns.
                # Since x is Log Price, volatility IS the standard deviation of returns.
                vol_est = returns_std[k] if k < len(returns_std) else 0.01
                if np.isnan(vol_est) or vol_est == 0: vol_est = 0.01

                R_dynamic = vol_est ** 2

                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q

                K[k] = Pminus[k] / (Pminus[k] + R_dynamic)
                xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
                P[k] = (1 - K[k]) * Pminus[k]

            # Convert back from Log Space
            return pd.Series(np.exp(xhat), index=series.index)
        except Exception as e:
            # print(f"Kalman Error: {e}")
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

    @staticmethod
    def calculate_momentum_decay(price_series: np.ndarray) -> float:
        """
        Atomic Physics: Half-life of a trend.
        Uses Ornstein-Uhlenbeck process to predict radioactive decay of momentum.
        """
        try:
            # Ensure numpy array
            z = np.array(price_series)
            if len(z) < 2: return 0.0

            z_lag = z[:-1]
            z_diff = z[1:] - z[:-1] # Equivalent to np.diff(z)

            # Fast linear regression for reversion speed (lambda)
            # lambda = - sum((x - mx)*(y - my)) / sum((x-mx)^2)
            m_x = np.mean(z_lag)
            m_y = np.mean(z_diff)

            denom = np.sum((z_lag - m_x)**2)
            if denom == 0:
                return 999.0

            lambda_val = -np.sum((z_lag - m_x) * (z_diff - m_y)) / denom

            if lambda_val <= 0: return 999.0 # Infinite trend
            return np.log(2) / lambda_val # Returns half-life in days
        except:
            return 999.0

    @staticmethod
    def generate_human_verdict(hurst, entropy, slope, price):
        """
        Centralized logic for Quantum Verdicts.
        Used by both Screener and Dashboard.
        """
        verdict = "WAIT"
        rationale = "No edge."

        if hurst is None: return "ERR", "No Data"

        # --- THE "REAL WORLD" THRESHOLDS ---
        # H > 0.55 is a Trend. H > 0.65 is a Super Trend.
        # Entropy < 0.8 (Normalized) is Organized.

        trend_strength = "Weak"
        if hurst > 0.62: trend_strength = "🔥 Strong"
        elif hurst > 0.55: trend_strength = "✅ Moderate"

        noise_level = "Noisy"
        if entropy < 0.6: noise_level = "💎 Crystal Clear"
        elif entropy < 0.85: noise_level = "🌊 Tradeable"

        # LOGIC TREE
        if hurst > 0.55 and entropy < 0.85:
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
