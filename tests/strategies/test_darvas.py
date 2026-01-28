import unittest
import pandas as pd
import numpy as np
from option_auditor.strategies.darvas import DarvasBoxStrategy

class TestDarvasBoxStrategy(unittest.TestCase):
    def test_darvas_breakout(self):
        # Create data with a clear box
        dates = pd.date_range(start="2023-01-01", periods=60, freq="B")

        # Make everything noisy so no accidental flat boxes (which trigger "top" logic)
        # Trend up slightly
        highs = np.linspace(100, 105, 60)
        lows = highs - 5
        closes = highs - 2
        volume = np.array([1000] * 60)

        # Insert a clear Box at the end.
        # Ceiling at 50.
        highs[48:53] = 110.0 # 48,49,50,51,52. Peak at 50.
        # Ensure neighbors are lower
        highs[47] = 108
        highs[53] = 108

        # Floor at 55.
        lows[53:58] = 95.0 # 53..57. Trough at 55.
        # Ensure neighbors are higher
        lows[52] = 97
        lows[58] = 97 # Index 58 is second to last.

        # Breakout at 59 (Last)
        # Close > Ceiling (110)
        closes[-1] = 112.0
        # Prev close inside
        closes[-2] = 105.0

        # Ensure lows/highs consistency at breakout
        highs[-1] = 113.0
        lows[-1] = 105.0

        df = pd.DataFrame({
            "Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": volume
        }, index=dates)

        strategy = DarvasBoxStrategy("TEST", df, check_mode=True)
        result = strategy.analyze()

        self.assertIsNotNone(result)
        self.assertEqual(result['signal'], "📦 DARVAS BREAKOUT")
        self.assertEqual(result['breakout_level'], 110.0)

    def test_insufficient_data(self):
        dates = pd.date_range(start="2023-01-01", periods=10, freq="B")
        df = pd.DataFrame({"Close": [100]*10}, index=dates)
        strategy = DarvasBoxStrategy("TEST", df)
        result = strategy.analyze()
        self.assertIsNone(result)
