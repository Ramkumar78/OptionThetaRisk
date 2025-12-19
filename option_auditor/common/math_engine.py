import numpy as np
import pandas as pd
from numba import njit
from scipy.stats import entropy
from pykalman import KalmanFilter

@njit(fastmath=True)
def _linear_regression_slope(x, y):
    """
    Manual linear regression slope calculation for Numba compatibility.
    """
    n = len(x)
    if n < 2: return 0.0

    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_xx = np.sum(x * x)

    denom = (n * sum_xx - sum_x * sum_x)
    if denom == 0: return 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    return slope

@njit(fastmath=True)
def calculate_hurst_exponent(price_series):
    """
    Random Process: Persistence vs Mean Reversion.
    H > 0.5: Trending (The physics of momentum is present)
    H < 0.5: Noise (Random walk, avoid)
    """
    if len(price_series) < 30:
        return 0.5

    lags = np.arange(2, 20) # Reduced max lag
    tau = np.empty(len(lags))

    for i in range(len(lags)):
        lag = lags[i]
        # Calculate standard deviation of differences
        # Numba prefers loops or simple array ops
        diff = price_series[lag:] - price_series[:-lag]
        tau[i] = np.std(diff)

    # Avoid log(0)
    valid_mask = tau > 0
    if not np.any(valid_mask):
        return 0.5

    log_lags = np.log(lags[valid_mask])
    log_tau = np.log(tau[valid_mask])

    slope = _linear_regression_slope(log_lags, log_tau)
    return slope * 2.0

@njit(fastmath=True)
def calculate_momentum_decay(price_series):
    """
    Atomic Physics: Half-life of a trend.
    Uses Ornstein-Uhlenbeck process to predict radioactive decay of momentum.
    """
    if len(price_series) < 2:
        return 0.0

    z = price_series
    z_lag = z[:-1]
    z_diff = z[1:] - z[:-1] # Equivalent to np.diff(z)

    # Fast linear regression for reversion speed (lambda)
    n = len(z_lag)
    m_x = np.mean(z_lag)
    m_y = np.mean(z_diff)

    # Avoid division by zero
    denom = np.sum((z_lag - m_x)**2)
    if denom == 0:
        return 999.0

    lambda_val = -np.sum((z_lag - m_x) * (z_diff - m_y)) / denom

    if lambda_val <= 0: return 999.0 # Infinite trend
    return np.log(2) / lambda_val # Returns half-life in days

def get_signal_entropy(price_series):
    """
    Thermodynamics: Shannon Entropy.
    Measures 'Market Heat Death'. High entropy = Pure Chaos.
    """
    if len(price_series) < 2:
        return 0.0

    # Calculate returns
    returns = np.diff(price_series) / price_series[:-1]

    # Histogram
    hist, _ = np.histogram(returns, bins=15, density=True)

    # Calculate entropy
    return entropy(hist + 1e-9)

def apply_kalman_filter(price_series):
    """
    Digital Signal Processing: NASA-grade noise removal.
    Replaces SMA-200 to eliminate lag in trend detection.
    """
    kf = KalmanFilter(transition_matrices=[1],
                      observation_matrices=[1],
                      initial_state_mean=price_series[0],
                      initial_state_covariance=1,
                      observation_covariance=1,
                      transition_covariance=0.01)
    state_means, _ = kf.filter(price_series)
    return state_means.flatten()
