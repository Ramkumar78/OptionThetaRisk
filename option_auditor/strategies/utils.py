import numpy as np

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
    # We need a fixed window. Let's look at the last 64 or 128 days (power of 2 is faster for FFT)
    N = len(prices)
    if N < 64: return None

    # Use most recent 64 days for cycle detection (short-term cycles)
    window_size = 64
    y = np.array(prices[-window_size:])
    x = np.arange(window_size)

    # 2. Detrend (Remove the linear trend so we just see waves)
    # Simple linear regression detrending
    p = np.polyfit(x, y, 1)
    trend = np.polyval(p, x)
    detrended = y - trend

    # Apply a window function (Hanning) to reduce edge leakage
    windowed = detrended * np.hanning(window_size)

    # 3. FFT
    fft_output = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(window_size)

    # 4. Find Dominant Frequency (ignore DC component at index 0)
    # We look for the peak amplitude
    amplitudes = np.abs(fft_output)

    # Skip low frequencies (trends) and very high frequencies (noise)
    # We want cycles between 3 days and 30 days usually.
    # Index 0 is trend.
    peak_idx = np.argmax(amplitudes[1:]) + 1

    dominant_freq = frequencies[peak_idx]
    period = 1.0 / dominant_freq if dominant_freq > 0 else 0

    # 5. Determine Phase (Where are we now?)
    # Reconstruct the dominant wave
    # Sine wave: A * sin(2*pi*f*t + phase)
    # We check the phase of the last point (t = window_size - 1)

    # Simple Heuristic: Check the detrended value relative to recent range
    # If detrended[-1] is near the minimum of the last cycle, we are at trough.

    current_val = detrended[-1]
    cycle_range = np.max(detrended) - np.min(detrended)

    # Normalized position (-1.0 to 1.0)
    rel_pos = current_val / (cycle_range / 2.0) if cycle_range > 1e-9 else 0.0

    return round(period, 1), rel_pos
