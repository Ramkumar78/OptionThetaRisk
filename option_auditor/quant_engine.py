import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend

class QuantPhysicsEngine:

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Robust Rescaled Range (R/S) Analysis.
        FIX: Enforces stricter data requirements to avoid 'ghost' signals.
        """
        try:
            if series.empty: return None

            # FIX 1: Strict Minimum Length (approx 6 months)
            # Statistical validity of Hurst degrades rapidly below 100 points.
            if len(series) < 100: return None

            # Prepare Returns (Log differences)
            returns = np.log(series / series.shift(1)).dropna()

            # Check for zero variance (Flatline stock)
            if returns.std() == 0: return 0.5

            # R/S Calculation Loop
            # Dynamic max_lag based on available history
            actual_max_lag = min(max_lag, len(returns) // 4)
            if actual_max_lag < 5: return None

            lags = range(2, actual_max_lag)
            rs_values = []

            for lag in lags:
                num_chunks = len(returns) // lag
                chunk_rs = []

                for i in range(num_chunks):
                    chunk = returns.iloc[i*lag : (i+1)*lag]

                    # Calculate Range and Standard Deviation
                    mean = chunk.mean()
                    cumsum_dev = (chunk - mean).cumsum()
                    R = cumsum_dev.max() - cumsum_dev.min()
                    S = chunk.std(ddof=1)

                    # Avoid division by zero
                    if S > 1e-9:
                        chunk_rs.append(R / S)

                if chunk_rs:
                    rs_values.append(np.mean(chunk_rs))

            # Linear Regression: log(R/S) = H * log(lag)
            if len(rs_values) < 3: return None

            # Filter out invalid lags
            valid_indices = np.where(np.array(rs_values) > 0)
            y = np.log(np.array(rs_values)[valid_indices])
            x = np.log(list(lags))[valid_indices]

            if len(x) < 3: return None

            H, _ = np.polyfit(x, y, 1)

            # Cap result (Financial time series bounds)
            return max(0.3, min(0.85, H))

        except Exception:
            return None

    @staticmethod
    def shannon_entropy(series: pd.Series, base=2) -> float:
        """
        Normalized Shannon Entropy.
        """
        try:
            data = series.pct_change().dropna()
            if len(data) < 30: return 1.0 # Insufficient data = Assumption of Chaos

            # Binning Strategy: Rice Rule or Sqrt
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
            return 1.0

    @staticmethod
    def kalman_filter(series: pd.Series) -> pd.Series:
        """
        Adaptive Kalman Filter on Log Prices.
        FIX: Adaptive Q (Process Noise) to reduce lag on volatile assets.
        """
        try:
            if (series <= 0).any(): return series

            # Work in Log Space to handle percentage moves linearly
            x = np.log(series.values)
            n_iter = len(x)
            sz = (n_iter,)

            # Rolling volatility (30-day) to estimate Measurement Noise (R)
            returns_std = series.pct_change().rolling(30).std().fillna(0.01).values

            xhat = np.zeros(sz)
            P = np.zeros(sz)
            xhatminus = np.zeros(sz)
            Pminus = np.zeros(sz)
            K = np.zeros(sz)

            xhat[0] = x[0]
            P[0] = 1.0

            # FIX 2: Adaptive Process Noise (Q)
            # If the stock is highly volatile, we assume the "True Value" moves faster.
            # We scale Q based on recent volatility.
            base_Q = 1e-5

            for k in range(1, n_iter):
                # Adaptive R (Measurement Noise)
                vol_est = returns_std[k] if k < len(returns_std) and not np.isnan(returns_std[k]) else 0.01
                vol_est = max(0.001, vol_est) # Clamp min vol

                R_dynamic = vol_est ** 2

                # Adaptive Q (Process Noise) - allow faster reaction in high vol regimes
                Q_adaptive = base_Q * (1 + (vol_est * 100))

                # Predict
                xhatminus[k] = xhat[k-1]
                Pminus[k] = P[k-1] + Q_adaptive

                # Update
                K[k] = Pminus[k] / (Pminus[k] + R_dynamic)
                xhat[k] = xhatminus[k] + K[k] * (x[k] - xhatminus[k])
                P[k] = (1 - K[k]) * Pminus[k]

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
        Verdict Logic V3: Explicit 'Casino Zone' identification.
        Slope: Expected as a DECIMAL percentage (0.01 = 1%).
        """
        if hurst is None: return "ERR", "Insufficient Data"

        # --- REGIME DEFINITIONS ---
        # H < 0.45       : Mean Reversion (Rubber Band)
        # 0.45 <= H <= 0.60 : RANDOM WALK (The Casino Zone) -> DO NOT TRADE
        # 0.60 < H <= 0.65  : Weak/Emerging Trend
        # H > 0.65       : Strong Trend (Persistence)

        # Slope Thresholds
        SIGNIFICANT_SLOPE = 0.015  # 1.5% move required to confirm trend direction

        verdict = "WAIT"
        rationale = "No distinct edge."

        # 1. MEAN REVERSION REGIME
        if hurst < 0.45:
            verdict = "REVERSAL (Mean Rev)"
            rationale = f"Price is elastic (H={hurst:.2f}). Fade extensions."

        # 2. RANDOM WALK REGIME (The 'Chop')
        elif 0.45 <= hurst <= 0.60:
            verdict = "RANDOM (Casino Zone)"
            rationale = f"Price action is noise (H={hurst:.2f}). Edge is zero."

        # 3. TREND REGIME
        elif hurst > 0.60:
            strength = "Weak" if hurst <= 0.65 else "🔥 Strong"

            # Filter by Entropy (Chaos)
            if entropy > 0.85:
                verdict = "CHOP (High Entropy)"
                rationale = "Trend exists but signal is too noisy/choppy."
            else:
                # Check Direction via Slope
                if slope > SIGNIFICANT_SLOPE:
                    verdict = f"BUY ({strength})"
                    rationale = f"Persistent Uptrend (H={hurst:.2f}) & Mom > 1.5%."
                elif slope < -SIGNIFICANT_SLOPE:
                    verdict = f"SHORT ({strength})"
                    rationale = f"Persistent Downtrend (H={hurst:.2f}) & Mom < -1.5%."
                else:
                    verdict = "WAIT (Flat)"
                    rationale = f"High persistence (H={hurst:.2f}) but Price is stalling."

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
