import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.unified_backtester import UnifiedBacktester

class TestUnifiedBacktester(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame mimicking yfinance download structure
        dates = pd.date_range(start="2022-01-01", periods=500)
        # Create a trend for Ticker
        close = np.linspace(100, 200, 500) # Bullish
        # Add a dip
        close[300:350] = np.linspace(160, 140, 50)

        data = pd.DataFrame({
            "Close": close,
            "High": close + 5,
            "Low": close - 5,
            "Open": close,
            "Volume": np.ones(500) * 1000000
        }, index=dates)

        # SPY Bullish
        spy_close = np.linspace(300, 400, 500)

        # VIX Low
        vix_close = np.ones(500) * 15.0

        # Construct the DataFrame that fetch_data would process
        # We need to simulate the result of yf.download([ticker, SPY, VIX])
        # In the real code, fetch_data calls yf.download and then manually constructs the single-level df.
        # So we can just mock fetch_data directly to return the pre-processed DF.

        self.processed_df = pd.DataFrame({
            'Close': close,
            'High': close + 5,
            'Low': close - 5,
            'Open': close,
            'Volume': np.ones(500) * 1000000,
            'Spy': spy_close,
            'Vix': vix_close
        }, index=dates)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_run_grandmaster_strategy(self, mock_fetch):
        mock_fetch.return_value = self.processed_df

        backtester = UnifiedBacktester("TEST", strategy_type="grandmaster")
        result = backtester.run()

        self.assertIn("strategy_return", result)
        self.assertIn("trades", result)
        # Should have bought because trend is up and regime is green
        self.assertTrue(result['trades'] > 0)
        self.assertEqual(result['strategy'], "GRANDMASTER")

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_run_turtle_strategy(self, mock_fetch):
        mock_fetch.return_value = self.processed_df

        backtester = UnifiedBacktester("TEST", strategy_type="turtle")
        result = backtester.run()

        self.assertIn("strategy_return", result)
        self.assertEqual(result['strategy'], "TURTLE")

if __name__ == '__main__':
    unittest.main()
