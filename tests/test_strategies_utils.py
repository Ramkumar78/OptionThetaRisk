import unittest
import numpy as np
from option_auditor.strategies.utils import calculate_dominant_cycle

class TestStrategyUtils(unittest.TestCase):
    def test_calculate_dominant_cycle_insufficient_data(self):
        prices = [100.0] * 10
        result = calculate_dominant_cycle(prices)
        self.assertIsNone(result)

    def test_calculate_dominant_cycle_sine_wave(self):
        # Generate a perfect sine wave with period 10
        # 64 points
        x = np.arange(64)
        period = 10
        # y = sin(2*pi*x/period)
        prices = 100 + 10 * np.sin(2 * np.pi * x / period)

        calculated_period, rel_pos = calculate_dominant_cycle(prices)

        # FFT precision might not be exact 10.0 due to discrete frequency bins
        # Frequency bins for N=64 are 0, 1/64, 2/64...
        # 1/10 = 0.1
        # 6/64 = 0.09375, 7/64 = 0.109375
        # It should pick one of these.
        # 1/0.09375 = 10.66, 1/0.109375 = 9.14

        self.assertTrue(9.0 <= calculated_period <= 11.0, f"Expected period ~10, got {calculated_period}")

        # Last point x=63. 63/10 = 6.3 cycles. 0.3 * 2pi is roughly positive.
        # sin(2*pi*6.3) = sin(0.6*pi) approx sin(108 deg) > 0
        # Let's check relative position logic roughly
        self.assertIsNotNone(rel_pos)

    def test_calculate_dominant_cycle_phase(self):
        # Test Trough (Bottom)
        # Cosine wave starts at top. cos(pi) = -1 (bottom)
        # Shifted to have bottom at end.
        x = np.arange(64)
        # Period 16.
        # We want the last point (63) to be a trough.
        # y = -cos(something)

        # Let's just construct data where the end is clearly the low point of the detrended series
        # Linear trend + Sine
        prices = np.linspace(100, 110, 64) + 5 * np.sin(2 * np.pi * x / 16)

        # Detrending should remove the linspace, leaving the sine.
        # We want to check if it runs without error and returns reasonable bounds
        per, pos = calculate_dominant_cycle(prices)

        self.assertTrue(14 <= per <= 18)
        self.assertTrue(-1.1 <= pos <= 1.1)

    def test_zero_variance(self):
        prices = [100.0] * 64
        per, pos = calculate_dominant_cycle(prices)
        # If flat, detrended is 0. cycle_range is 0. pos is 0.
        # FFT of 0 is 0. Peak index ?
        # argmax([0,0,0...]) -> 0. freq[1] -> 1/64.
        # Period 64.
        self.assertIsNotNone(per)
        self.assertEqual(pos, 0)
