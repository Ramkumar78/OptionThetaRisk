from .base import BaseStrategy
import pandas as pd
import numpy as np

class FourierStrategy(BaseStrategy):
    def _calculate_dominant_cycle(self, prices):
        """
        Uses FFT to find the dominant cycle period (in days).
        Returns: (period_days, current_phase_position)
        """
        N = len(prices)
        if N < 64: return None

        window_size = 64
        y = np.array(prices[-window_size:])
        x = np.arange(window_size)

        # Detrend
        p = np.polyfit(x, y, 1)
        trend = np.polyval(p, x)
        detrended = y - trend

        # Window
        windowed = detrended * np.hanning(window_size)

        # FFT
        fft_output = np.fft.rfft(windowed)
        frequencies = np.fft.rfftfreq(window_size)

        amplitudes = np.abs(fft_output)

        # Peak (ignore DC)
        if len(amplitudes) < 2: return None
        peak_idx = np.argmax(amplitudes[1:]) + 1

        dominant_freq = frequencies[peak_idx]
        period = 1.0 / dominant_freq if dominant_freq > 0 else 0

        # Phase position
        current_val = detrended[-1]
        cycle_range = np.max(detrended) - np.min(detrended)
        rel_pos = current_val / (cycle_range / 2.0) if cycle_range > 0 else 0

        return round(period, 1), rel_pos

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 100:
            return {'signal': 'WAIT'}

        closes = df['Close'].tolist()
        cycle_data = self._calculate_dominant_cycle(closes)

        if not cycle_data:
            return {'signal': 'WAIT'}

        period, rel_pos = cycle_data

        signal = "WAIT"

        if 5 <= period <= 60:
            if rel_pos <= -0.8:
                signal = "BUY"
            elif rel_pos >= 0.8:
                signal = "SELL"
            elif -0.2 <= rel_pos <= 0.2:
                signal = "NEUTRAL"

        return {
            "signal": signal,
            "period": period,
            "rel_pos": rel_pos
        }
