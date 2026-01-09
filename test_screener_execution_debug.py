import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import logging
from option_auditor.screener import screen_fourier_cycles, screen_dynamic_volatility_fortress

# Configure logging to see errors
logging.basicConfig(level=logging.ERROR)

class TestScreenerExecution(unittest.TestCase):
    @patch('option_auditor.screener.fetch_batch_data_safe')
    @patch('option_auditor.common.data_utils.get_cached_market_data')
    def test_screeners_run(self, mock_cached, mock_batch):
        # Mock DataFrame with required columns
        dates = pd.date_range('2023-01-01', periods=200)
        df = pd.DataFrame({
            'Open': np.linspace(100, 150, 200),
            'High': np.linspace(105, 155, 200),
            'Low': np.linspace(95, 145, 200),
            'Close': np.linspace(100, 150, 200),
            'Volume': [1000000]*200
        }, index=dates)

        # Ensure Fortress logic passes (ATR > 2%, VIX < 20)
        # Price 150. ATR needs to be > 3.0.
        # Let's make high/low volatile
        df['High'] = df['Close'] + 5
        df['Low'] = df['Close'] - 5

        mock_data = pd.concat([df], axis=1, keys=['AAPL'])
        mock_batch.return_value = mock_data
        mock_cached.return_value = mock_data

        print("Testing Fortress...")
        with patch('option_auditor.screener._get_market_regime', return_value=15.0):
             # Ensure we pass a list so it uses our mock data for that list
             res = screen_dynamic_volatility_fortress(ticker_list=['AAPL'])
             if len(res) == 0:
                 print("Fortress result empty. Check logs.")
             else:
                 print(f"Fortress result keys: {res[0].keys()}")
             self.assertTrue(len(res) > 0, "Fortress returned empty")
             self.assertIn('breakout_date', res[0])

if __name__ == '__main__':
    unittest.main()
