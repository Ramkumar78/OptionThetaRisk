import numpy as np
import pandas as pd
from scipy.signal import hilbert, detrend
from scipy.stats import norm

def calculate_hurst(series: pd.Series, max_lag=20) -> float:
    """
    Robust Rescaled Range (R/S) Analysis.
    Returns Hurst Exponent (H).
    """
    try:
        if series.empty: return None

        # Require N > 100 for statistical significance
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

        return H

    except Exception:
        return None

def shannon_entropy(series: pd.Series, base=2) -> float:
    """
    Normalized Shannon Entropy.
    Returns value between 0 (Order) and 1 (Chaos).
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

def kalman_filter(series: pd.Series, optimization_window: int = 30) -> pd.Series:
    """
    Adaptive Kalman Filter on Log Prices.
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
            innovation = x[k] - xhatminus[k]
            alpha = 0.1 # Smoothing factor
            Q_val = (1 - alpha) * Q_val + alpha * (innovation**2)

        return pd.Series(np.exp(xhat), index=series.index)
    except Exception:
        return series

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

def generate_human_verdict(hurst, entropy, slope, price):
    """
    Verdict Logic: Handling raw/None values
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

def calculate_hilbert_phase(prices):
    """
    Calculates Instantaneous Phase using the Hilbert Transform.
    Returns:
        - phase: (-pi to +pi) where -pi/pi is a trough/peak.
        - amplitude: Magnitude of the cycle (Amplitude).
    """
    try:
        if len(prices) < 30: return None, None

        # 1. Log Returns to normalize magnitude
        log_prices = np.log(prices)

        # 2. Detrend (Linear) to isolate oscillatory component
        detrended = detrend(log_prices, type='linear')

        # 3. Apply Hilbert Transform to get Analytic Signal
        analytic_signal = hilbert(detrended)

        # 4. Extract Phase (Angle) and Amplitude (Abs)
        phase = np.angle(analytic_signal)[-1]
        amplitude = np.abs(analytic_signal)[-1]

        return phase, amplitude

    except Exception:
        return None, None

def calculate_dominant_cycle(prices):
    """
    Uses FFT to find the dominant cycle period (in days) of a price series.
    Returns: (period_days, current_phase_position)

    current_phase_position:
       0.0 = Bottom (Trough) -> Ideal Buy
       0.5 = Top (Peak)      -> Ideal Sell
       (Approximate sine wave mapping)
    """
    # 1. Prepare Data
    N = len(prices)
    if N < 64: return None

    # Use most recent 64 days for cycle detection (short-term cycles)
    window_size = 64
    y = np.array(prices[-window_size:])
    x = np.arange(window_size)

    # 2. Detrend
    p = np.polyfit(x, y, 1)
    trend = np.polyval(p, x)
    detrended = y - trend

    # Apply a window function (Hanning)
    windowed = detrended * np.hanning(window_size)

    # 3. FFT
    fft_output = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(window_size)

    # 4. Find Dominant Frequency
    amplitudes = np.abs(fft_output)

    # Skip DC component at index 0
    peak_idx = np.argmax(amplitudes[1:]) + 1

    dominant_freq = frequencies[peak_idx]
    period = 1.0 / dominant_freq if dominant_freq > 0 else 0

    # 5. Determine Phase
    current_val = detrended[-1]
    cycle_range = np.max(detrended) - np.min(detrended)

    # Normalized position (-1.0 to 1.0)
    rel_pos = current_val / (cycle_range / 2.0) if cycle_range > 0 else 0

    return round(period, 1), rel_pos

def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    """
    Calculates Black-Scholes Greeks for European options.

    Parameters:
    - S: Underlying Price
    - K: Strike Price
    - T: Time to Expiration (in years)
    - r: Risk-Free Interest Rate (decimal, e.g. 0.05)
    - sigma: Volatility (decimal, e.g. 0.20)
    - option_type: "call" or "put"

    Returns:
    - Dict with Delta, Gamma, Theta, Vega, Rho
    """
    try:
        # Validate inputs
        if T <= 0:
            # Expired: Intrinsic value Greeks
            delta = 0.0
            if option_type.lower() == "call":
                delta = 1.0 if S > K else 0.0
            else:
                delta = -1.0 if S < K else 0.0
            return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

        if sigma <= 0: sigma = 1e-5 # Avoid division by zero

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        is_call = option_type.lower() == "call"

        # Delta
        if is_call:
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        # Gamma (Same for Call and Put)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

        # Vega (Same for Call and Put) - expressed per 1% vol change usually, but here raw.
        # Often Vega is quoted for 1% change, so multiply by 0.01.
        # But standard BS formula gives change per 100% vol change (unit vol).
        # We will return raw BS vega (change per 1 unit of sigma), but frontend usually expects per 1%?
        # Standard convention: Vega = S * sqrt(T) * N'(d1) * 0.01 (if per 1%)
        # Here we return "Mathematical Vega" (per 100% vol).
        # To display nicely, we usually divide by 100 later. Let's return strict math value.
        vega = S * np.sqrt(T) * norm.pdf(d1)

        # Theta (Annualized)
        if is_call:
            theta_part1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
            theta_part2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
            theta = theta_part1 + theta_part2
        else:
            theta_part1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
            theta_part2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
            theta = theta_part1 + theta_part2

        # Convert Theta to Daily (approx)
        theta_daily = theta / 365.0

        # Rho
        if is_call:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "theta": float(theta_daily), # Daily Theta
            "vega": float(vega / 100.0), # Vega per 1% vol change
            "rho": float(rho / 100.0)    # Rho per 1% rate change
        }

    except Exception as e:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0, "error": str(e)}
