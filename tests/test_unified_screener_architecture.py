import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.unified_screener import screen_universal_dashboard
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.fourier import FourierStrategy

class TestUnifiedScreenerArchitecture(unittest.TestCase):

    def setUp(self):
        # Create a sample DataFrame that simulates a bullish trend and breakout
        # 100 days of data
        dates = pd.date_range(start="2023-01-01", periods=100)
        close = np.linspace(100, 150, 100) # Linear uptrend
        # Add a breakout at the end
        close[-1] = 155
        # Add some volatility
        high = close + 2
        low = close - 2
        volume = np.random.randint(1000000, 2000000, 100)

        self.mock_df = pd.DataFrame({
            "Open": close,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume
        }, index=dates)

        # For multi-index simulation (batch download result)
        self.mock_batch_df = pd.concat([self.mock_df], axis=1, keys=["AAPL"])

    @patch("option_auditor.common.data_utils.fetch_batch_data_safe")
    def test_screen_universal_dashboard_flow(self, mock_fetch):
        # Setup mock return
        mock_fetch.return_value = self.mock_batch_df

        # Test with explicit list
        results = screen_universal_dashboard(["AAPL"])

        self.assertTrue(len(results) > 0)
        res = results[0]
        self.assertEqual(res['ticker'], "AAPL")
        self.assertIn("turtle", res['strategies'])
        self.assertIn("isa", res['strategies'])
        self.assertIn("fourier", res['strategies'])
        self.assertIn("master_verdict", res)
        self.assertIn("confluence_score", res)

    def test_turtle_strategy(self):
        strat = TurtleStrategy()
        # Create a DF where current close > 20-day max
        df = self.mock_df.copy()
        # Make the last close significantly higher than previous 20 day high
        # Use loc to avoid ChainedAssignmentError
        df.loc[df.index[-1], 'Close'] = 200.0

        res = strat.analyze(df)
        self.assertEqual(res['signal'], 'BUY')
        self.assertGreater(res['target'], 200)

    def test_isa_strategy(self):
        strat = IsaStrategy()
        # Ensure SMA 200 condition met
        dates = pd.date_range(start="2023-01-01", periods=201)
        close = np.linspace(100, 200, 201)
        df = pd.DataFrame({
            "High": close + 5,
            "Low": close - 5,
            "Close": close,
            "Volume": np.ones(201) * 1000000
        }, index=dates)

        # Current close (200).
        # Previous High 50 needs to be exceeded.
        # Linear uptrend: High[-2] is 199+5 = 204.
        # Current Close 200 < 204.
        # Force breakout:
        df.loc[df.index[-1], 'Close'] = 210.0 # Breakout above 204

        res = strat.analyze(df)
        self.assertEqual(res['signal'], 'BUY')

    def test_fourier_strategy(self):
        strat = FourierStrategy()
        # Generate a sine wave
        x = np.linspace(0, 4*np.pi, 100)
        y = np.sin(x) + 10
        dates = pd.date_range(start="2023-01-01", periods=100)
        df = pd.DataFrame({"Close": y}, index=dates)

        res = strat.analyze(df)
        # Should detect cycle
        self.assertIn(res['signal'], ['BUY', 'SELL', 'NEUTRAL', 'WAIT'])
        if res['signal'] != 'WAIT':
            self.assertIsNotNone(res['period'])

if __name__ == '__main__':
    unittest.main()
