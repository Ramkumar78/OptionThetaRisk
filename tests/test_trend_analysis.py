import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from option_auditor.common.data_utils import _calculate_trend_breakout_date

class TestTrendAnalysis(unittest.TestCase):

    def setUp(self):
        # Create a base date range for 60 days
        self.dates = pd.date_range(end=datetime.now(), periods=60, freq='D')

    def test_insufficient_data(self):
        # Create a DataFrame with only 40 rows
        dates = self.dates[:40]
        df = pd.DataFrame({
            'Open': np.random.rand(40) * 100,
            'High': np.random.rand(40) * 105,
            'Low': np.random.rand(40) * 95,
            'Close': np.random.rand(40) * 100,
            'Volume': np.random.randint(1000, 10000, 40)
        }, index=dates)

        result = _calculate_trend_breakout_date(df)
        self.assertEqual(result, "N/A")

    def test_trend_broken(self):
        # Create a scenario where the trend is broken (Close <= Low_20)
        # We need enough data (60 days) to calculate High_50 and Low_20

        # Construct data to ensure Low_20 is calculable
        # Low_20 is min(Low) over last 20 days, shifted by 1.

        # Let's make a clear uptrend first, then a crash at the end.
        closes = np.linspace(100, 200, 60)
        highs = closes + 5
        lows = closes - 5

        # At the very end (last row), we crash the price below the recent Low_20
        # Recent Low_20 would be around 190 (since we are at 200).
        # Let's set the last Close to 150.

        closes[-1] = 150

        df = pd.DataFrame({
            'Open': closes, # Simplified
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': 10000
        }, index=self.dates)

        result = _calculate_trend_breakout_date(df)
        self.assertEqual(result, "N/A")

    def test_clear_breakout(self):
        # Scenario:
        # Days 0-49: Highs are at 100.
        # Day 50: High_50 calculation looks at 0-49. Max is 100.
        # Day 51: Breakout! Close = 105.
        # Days 52-59: Stay high to keep trend active.

        data_len = 60
        closes = np.full(data_len, 90.0)
        highs = np.full(data_len, 100.0)
        lows = np.full(data_len, 80.0)

        # Create the breakout at index 51 (Day 51)
        # We need Close >= High_50.
        # High_50 at index 51 is max(Highs[1:51]) (since shift 1 means looking at previous 50).

        # Let's set index 51 to be the breakout.
        # We need High_50 at index 51 to be <= Close at index 51.
        # Highs 0-50 are 100.
        # So High_50 at index 51 is 100.
        # Set Close at index 51 to 101.

        closes[51] = 101.0
        highs[51] = 102.0 # High must be at least Close

        # Ensure we stay above Low_20
        # Low_20 will be based on recent lows of 80.
        # We need Close > 80.

        # Let's keep price high after breakout
        closes[52:] = 102.0
        highs[52:] = 103.0
        lows[52:] = 95.0

        df = pd.DataFrame({
            'Open': closes,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': 10000
        }, index=self.dates)

        # Expected breakout date is the date at index 51
        expected_date = self.dates[51].strftime("%Y-%m-%d")

        result = _calculate_trend_breakout_date(df)
        self.assertEqual(result, expected_date)

if __name__ == '__main__':
    unittest.main()
