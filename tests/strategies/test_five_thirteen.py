import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch
from option_auditor.strategies.five_thirteen import FiveThirteenStrategy

class TestFiveThirteenStrategy(unittest.TestCase):
    def create_mock_df(self, periods=30):
        dates = pd.date_range(start="2023-01-01", periods=periods, freq="B")
        close = np.linspace(100, 110, periods)
        high = close + 1
        low = close - 1
        return pd.DataFrame({
            "Open": close, "High": high, "Low": low, "Close": close, "Volume": 1000
        }, index=dates)

    def test_fresh_breakout_5_21(self):
        df = self.create_mock_df(30)
        # Mock EMAs to trigger breakout
        # Prev: 5 < 21. Curr: 5 > 21.

        with patch('pandas_ta.ema') as mock_ema:
            # We need 3 series: 5, 13, 21
            # Last 2 values matter.
            # 5:  [..., 100, 110]
            # 13: [..., 105, 106]
            # 21: [..., 108, 109]

            s_5 = pd.Series([0]*28 + [100, 110], index=df.index)
            s_13 = pd.Series([0]*28 + [105, 106], index=df.index)
            s_21 = pd.Series([0]*28 + [108, 109], index=df.index)

            mock_ema.side_effect = [s_5, s_13, s_21]

            strategy = FiveThirteenStrategy("TEST", df)
            result = strategy.analyze()

            self.assertIsNotNone(result)
            self.assertIn("FRESH 5/21 BREAKOUT", result['signal'])
            self.assertEqual(result['color'], "green")

    def test_trending_5_13(self):
        df = self.create_mock_df(30)

        with patch('pandas_ta.ema') as mock_ema:
            # 5 > 13 for both prev and curr
            # 5:  [..., 110, 112]
            # 13: [..., 105, 106]
            # 21: [..., 100, 101] # 5 > 21 too, so it might hit 5/21 trending priority

            # To hit 5/13 trending specifically, we need 5 < 21 but 5 > 13
            # 5:  [..., 108, 109]
            # 13: [..., 105, 106]
            # 21: [..., 110, 111]

            s_5 = pd.Series([0]*28 + [108, 109], index=df.index)
            s_13 = pd.Series([0]*28 + [105, 106], index=df.index)
            s_21 = pd.Series([0]*28 + [110, 111], index=df.index)

            mock_ema.side_effect = [s_5, s_13, s_21]

            strategy = FiveThirteenStrategy("TEST", df)
            result = strategy.analyze()

            self.assertIsNotNone(result)
            self.assertIn("5/13 TRENDING", result['signal'])
            self.assertEqual(result['color'], "blue")
