import pytest
import numpy as np
import pandas as pd
from option_auditor.strategies.math_utils import (
    calculate_hurst,
    shannon_entropy,
    kalman_filter,
    calculate_momentum_decay,
    generate_human_verdict,
    calculate_hilbert_phase,
    calculate_dominant_cycle
)

# Test calculate_hurst
def test_calculate_hurst_random_walk():
    # Random walk should have H approx 0.5
    np.random.seed(42)
    # Use Geometric Brownian Motion for Random Walk
    # Log returns are i.i.d. Normal -> Random Walk in log-price
    returns = np.random.randn(2000) * 0.01
    series = pd.Series(100 * np.exp(np.cumsum(returns)))

    # Use larger max_lag to reduce small-sample bias
    # Default max_lag=20 tends to overestimate H (~0.75 for RW)
    # With max_lag=300, we observe ~0.61
    h = calculate_hurst(series, max_lag=300)

    assert h is not None
    assert 0.55 < h < 0.65

def test_calculate_hurst_trending():
    # Persistent series (Positive autocorrelation in returns) -> H > 0.5 (and > RW)
    np.random.seed(42)
    returns = [0]
    for _ in range(2000):
        # AR(1) with positive coefficient creates memory
        returns.append(0.5 * returns[-1] + np.random.randn())

    r = np.array(returns) * 0.01
    series = pd.Series(100 * np.exp(np.cumsum(r)))

    h = calculate_hurst(series, max_lag=300)
    assert h is not None
    assert h > 0.65

def test_calculate_hurst_mean_reverting():
    # Mean reverting should have H < 0.5
    np.random.seed(42)
    # Mean reverting process (Ornstein-Uhlenbeck)
    mu = 100
    theta = 0.1
    sigma = 1.0
    prices = [100]
    for _ in range(2000):
        dy = theta * (mu - prices[-1]) + sigma * np.random.randn()
        prices.append(prices[-1] + dy)

    series = pd.Series(prices)
    # Ensure all positive
    if series.min() <= 0:
        series = series - series.min() + 10

    h = calculate_hurst(series, max_lag=300)
    assert h is not None
    # Mean reversion H should be low (anti-persistent)
    assert h < 0.5

def test_calculate_hurst_edge_cases():
    assert calculate_hurst(pd.Series([])) is None
    assert calculate_hurst(pd.Series([1]*50)) is None # Too short (<100)

# Test shannon_entropy
def test_shannon_entropy_random():
    np.random.seed(42)
    series = pd.Series(np.random.randn(200) + 100)
    entropy = shannon_entropy(series)
    # High entropy for random noise
    assert entropy is not None
    assert entropy > 0.8

def test_shannon_entropy_constant():
    # Geometric progression: constant pct_change
    series = pd.Series([100 * (1.01)**i for i in range(200)])
    entropy = shannon_entropy(series)
    assert entropy is not None
    assert 0 <= entropy <= 1

def test_shannon_entropy_short():
    assert shannon_entropy(pd.Series(range(10))) is None

# Test kalman_filter
def test_kalman_filter_smoothing():
    np.random.seed(42)
    # True signal: linear trend
    true_signal = np.linspace(100, 200, 100)
    # Noisy observation
    noisy_signal = true_signal + np.random.normal(0, 5, 100)
    series = pd.Series(noisy_signal)

    filtered = kalman_filter(series)

    assert len(filtered) == len(series)
    # Filtered should be smoother, i.e., lower standard deviation of differences
    noisy_diff_std = np.diff(series).std()
    filtered_diff_std = np.diff(filtered).std()
    assert filtered_diff_std < noisy_diff_std

def test_kalman_filter_preserves_trend():
    series = pd.Series(np.linspace(100, 200, 50))
    filtered = kalman_filter(series)
    # Should closely track the trend.
    # The filter takes some time to converge, so check later part
    assert np.allclose(filtered.iloc[-10:], series.iloc[-10:], rtol=0.05)

# Test calculate_momentum_decay
def test_calculate_momentum_decay():
    # Exponential decay
    t = np.arange(100)
    half_life_days = 10
    lambda_val = np.log(2) / half_life_days
    decay_series = 100 * np.exp(-lambda_val * t)

    calc_half_life = calculate_momentum_decay(decay_series)

    # Should be reasonably close
    assert np.isclose(calc_half_life, half_life_days, rtol=0.2)

def test_calculate_momentum_decay_short():
    assert calculate_momentum_decay(np.array([1])) == 0.0

# Test generate_human_verdict
def test_generate_human_verdict_mean_rev():
    verdict, rationale = generate_human_verdict(hurst=0.3, entropy=0.5, slope=0.1, price=100)
    assert "REVERSAL" in verdict
    assert "Elastic Price" in rationale

def test_generate_human_verdict_random():
    verdict, rationale = generate_human_verdict(hurst=0.5, entropy=0.5, slope=0.1, price=100)
    assert "RANDOM" in verdict
    assert "Pure Noise" in rationale

def test_generate_human_verdict_trend_buy():
    verdict, rationale = generate_human_verdict(hurst=0.7, entropy=0.5, slope=0.02, price=100)
    assert "BUY" in verdict
    assert "Persistent Uptrend" in rationale

def test_generate_human_verdict_trend_short():
    verdict, rationale = generate_human_verdict(hurst=0.7, entropy=0.5, slope=-0.02, price=100)
    assert "SHORT" in verdict
    assert "Persistent Downtrend" in rationale

def test_generate_human_verdict_insufficient():
    verdict, rationale = generate_human_verdict(hurst=None, entropy=0.5, slope=0.1, price=100)
    assert verdict == "ERR"
    assert "Insufficient Data" in rationale

# Test calculate_hilbert_phase
def test_calculate_hilbert_phase():
    t = np.linspace(0, 4*np.pi, 200)
    series = 100 + 10 * np.sin(t)
    phase, amplitude = calculate_hilbert_phase(series)

    assert phase is not None
    assert amplitude is not None
    assert -np.pi <= phase <= np.pi
    assert amplitude > 0

def test_calculate_hilbert_phase_short():
    phase, amp = calculate_hilbert_phase(np.array([1, 2, 3]))
    assert phase is None
    assert amp is None

# Test calculate_dominant_cycle
def test_calculate_dominant_cycle():
    # Generate signal with period 20 days
    t = np.arange(200)
    period = 20
    freq = 1 / period
    signal = 10 * np.sin(2 * np.pi * freq * t) + 100

    calc_period, phase_pos = calculate_dominant_cycle(signal)

    assert calc_period is not None
    assert calc_period > 0
    # Expected freq approx 1/20 = 0.05
    # Depending on resolution, it should be somewhat close
    assert 10 <= calc_period <= 30

def test_calculate_dominant_cycle_short():
    assert calculate_dominant_cycle(range(10)) is None
