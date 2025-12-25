import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend

class QuantPhysicsEngine:

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Robust Rescaled Range (R/S) Analysis.
        FIX: Removed artificial clamping [0.3, 0.85].
        True anomalies (H > 0.9) are now visible.
        """
        try:
            if series.empty: return None

            # FIX: Require N > 100 for statistical significance
            if len(series) < 100: return None

            # Prepare Returns (Log differences)
            returns = np.log(series / series.shift(1)).dropna()

            if returns.std() == 0: return 0.5

            # Dynamic max_lag
            actual_max_lag = min(max_lag, len(returns) // 4)
            if actual_max_lag < 5: return None

            lags = range(2, actual_max_lag)
            rs_values = []

            for lag in lags:
                num_chunks = len(returns) // lag
                chunk_rs = []

                for i in range(num_chunks):
                    chunk = returns.iloc[i*lag : (i+1)*lag]
                    mean = chunk.mean()
                    cumsum_dev = (chunk - mean).cumsum()
                    R = cumsum_dev.max() - cumsum_dev.min()
                    S = chunk.std(ddof=1)

                    if S > 1e-9:
                        chunk_rs.append(R / S)

                if chunk_rs:
                    rs_values.append(np.mean(chunk_rs))

            if len(rs_values) < 3: return None

            # Log-Log Regression
            valid_indices = np.where(np.array(rs_values) > 0)
            y = np.log(np.array(rs_values)[valid_indices])
            x = np.log(list(lags))[valid_indices]

            if len(x) < 3: return None

            H, _ = np.polyfit(x, y, 1)

            # Return raw H.
            # Values > 1.0 or < 0.0 indicate extreme statistical artifacts or strong memory.
            return H

        except Exception:
            return None

    @staticmethod
    def shannon_entropy(series: pd.Series, base=2) -> float:
        """
        Normalized Shannon Entropy.
        FIX: Returns None instead of default 1.0 if data is insufficient.
        """
        try:
            data = series.pct_change().dropna()
            if len(data) < 100: return None # Insufficient for distribution analysis

            num_bins = int(len(data) ** 0.5)
            counts, _ = np.histogram(data, bins=num_bins, density=False)

            probs = counts / np.sum(counts)
            probs = probs[probs > 0]

            S = -np.sum(probs * np.log(probs) / np.log(base))
            max_S = np.log(num_bins) / np.log(base)

            if max_S == 0: return 1.0

            normalized_entropy = S / max_S
            return normalized_entropy
        except:
            return None

    @staticmethod
    def kalman_filter(series: pd.Series, optimization_window: int = 30) -> pd.Series:
        """
        Adaptive Kalman Filter on Log Prices.
        FIX: Removed 'Magic Number' 100. Implemented Adaptive Q based on innovation variance.
        """
        try:
            if (series <= 0).any(): return series

            x = np.log(series.values)
            n_iter = len(x)
            sz = (n_iter,)

            xhat = np.zeros(sz)      # Posteriori estimate
            P = np.zeros(sz)         # Posteriori error covariance
            xhatminus = np.zeros(sz) # Priori estimate
            Pminus = np.zeros(sz)    # Priori error covariance
            K = np.zeros(sz)         # Gain

            xhat[0] = x[0]
            P[0] = 1.0

            # Estimate initial Measurement Noise (R) from history
            if n_iter > optimization_window:
                R_val = max(1e-5, np.var(np.diff(x[:optimization_window])))
            else:
                R_val = 1e-4

            # Initial Process Noise (Q)
            Q_val = 1e-5

            for k in range(1, n_iter):
                # Time Update
                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q_val

                # Measurement Update
                K[k] = Pminus[k] / (Pminus[k] + R_val)
                xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
                P[k] = (1 - K[k]) * Pminus[k]

                # Adaptive Q: Update based on squared prediction error (Innovation)
                # If model misses reality (innovation is high), increase Q to allow faster adaptation
                innovation = x[k] - xhatminus[k]
                alpha = 0.1 # Smoothing factor
                Q_val = (1 - alpha) * Q_val + alpha * (innovation**2)

            return pd.Series(np.exp(xhat), index=series.index)
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
        Verdict Logic V3.1: Handling raw/None values
        """
        if hurst is None: return "ERR", "Insufficient Data"

        # Handle cases where entropy is None but Hurst calculated
        entropy_val = entropy if entropy is not None else 1.0

        verdict = "WAIT"
        rationale = "No distinct edge."

        # 1. MEAN REVERSION
        if hurst < 0.45:
            verdict = "REVERSAL (Mean Rev)"
            rationale = f"Elastic Price (H={hurst:.2f}). Fade moves."

        # 2. RANDOM WALK (Casino Zone)
        elif 0.45 <= hurst <= 0.60:
            verdict = "RANDOM (Casino Zone)"
            rationale = f"Pure Noise (H={hurst:.2f}). No statistical edge."

        # 3. TREND REGIME
        elif hurst > 0.60:
            strength = "Weak" if hurst <= 0.65 else "🔥 Strong"

            if entropy_val > 0.85:
                verdict = "CHOP (High Entropy)"
                rationale = "Trend exists but signal is too noisy."
            else:
                # Slope check
                if slope > 0.015:
                    verdict = f"BUY ({strength})"
                    rationale = f"Persistent Uptrend (H={hurst:.2f})."
                elif slope < -0.015:
                    verdict = f"SHORT ({strength})"
                    rationale = f"Persistent Downtrend (H={hurst:.2f})."
                else:
                    verdict = "WAIT (Stalling)"
                    rationale = f"High persistence (H={hurst:.2f}) but no momentum."

        return verdict, rationale

    @staticmethod
    def analyze_breakout(ticker, df):
        """
        Analyzes if a stock has broken out of a 6-month range and when.
        """
        # 1. Ensure we have enough data (approx 126 trading days in 6 months)
        if len(df) < 120:
            return {"signal": False, "breakout_date": None}

        # 2. Define the "Lookback" vs "Recent" window
        # We look for a breakout that happened in the last 30 days
        # relative to the high of the prior 5 months.
        recent_window = 30
        historical_window = len(df) - recent_window

        # Get the data subsets
        history_df = df.iloc[:historical_window]
        recent_df = df.iloc[historical_window:]

        # 3. Calculate the Resistance Level (Max High of the previous period)
        resistance_level = history_df['Close'].max()

        # 4. Check for Breakout in the recent window
        # Find days where Close > Resistance Level
        breakout_mask = recent_df['Close'] > resistance_level

        if not breakout_mask.any():
            return {"signal": False, "breakout_date": None}

        # 5. Find the FIRST date the breakout occurred in this recent window
        breakout_dates = recent_df[breakout_mask].index
        first_breakout_date = breakout_dates[0]

        # Calculate days since breakout
        days_since = (df.index[-1] - first_breakout_date).days

        return {
            "signal": True,
            "breakout_date": first_breakout_date.strftime('%Y-%m-%d'), # Format date string
            "days_since": days_since,
            "resistance_level": resistance_level,
            "current_price": df['Close'].iloc[-1]
        }
