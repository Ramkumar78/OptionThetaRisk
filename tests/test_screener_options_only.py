import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date, timedelta
from option_auditor.screener import screen_options_only_strategy

class TestScreenerOptionsOnly(unittest.TestCase):

    @patch('yfinance.Ticker')
    @patch('pandas.read_csv')
    @patch('os.path.exists')
    def test_screen_options_only_valid_data(self, mock_exists, mock_read_csv, mock_ticker):
        # Mock file existence and reading
        mock_exists.return_value = True
        mock_read_csv.return_value = pd.DataFrame({'Symbol': ['AAPL']})

        # Mock Ticker object
        mock_tk = MagicMock()
        mock_ticker.return_value = mock_tk

        # Mock History (Liquidity Check) - 5 days, High Volume
        # Must return valid dataframe with 'Close' and 'Volume'
        mock_tk.history.return_value = pd.DataFrame({
            'Close': [150.0] * 5,
            'Volume': [20_000_000] * 5
        })

        # Mock Calendar (Earnings)
        mock_tk.calendar = {'Earnings Date': [pd.Timestamp(date.today() + timedelta(days=90))]}

        # Mock Options Expirations
        target_date = date.today() + timedelta(days=45)
        mock_tk.options = [target_date.strftime('%Y-%m-%d')]

        # Mock Option Chain
        mock_chain = MagicMock()

        # Puts Data
        # Ensure we construct the DataFrame correctly to match what screener expects
        puts_data = {
            'strike': [130.0, 135.0, 140.0, 145.0, 150.0],
            'bid': [1.0, 1.5, 3.0, 4.0, 6.0], # 140 strike bid 3.0
            'ask': [1.0, 1.0, 3.2, 4.2, 6.2], # 135 strike ask 1.0
            'lastPrice': [1.1, 1.6, 2.6, 4.1, 6.1],
            'impliedVolatility': [0.4, 0.4, 0.4, 0.4, 0.4]
        }
        # Credit = 3.0 - 1.0 = 2.0
        # Width = 5. Risk = 3.0. ROC = 66%

        mock_chain.puts = pd.DataFrame(puts_data)
        mock_tk.option_chain.return_value = mock_chain

        # Run Screener
        results = screen_options_only_strategy(limit=1)

        # Assertions
        self.assertEqual(len(results), 1)
        result = results[0]

        # Verify Keys for UI
        expected_keys = [
            'ticker', 'price', 'verdict', 'setup_name', 'short_put',
            'long_put', 'expiry_date', 'dte', 'credit', 'risk',
            'roc', 'earnings_gap', 'delta'
        ]
        for key in expected_keys:
            self.assertIn(key, result)

        self.assertEqual(result['ticker'], 'AAPL')
        self.assertEqual(result['price'], 150.0)
        self.assertEqual(result['verdict'], "🟢 GREEN LIGHT")

    @patch('yfinance.Ticker')
    @patch('pandas.read_csv')
    @patch('os.path.exists')
    def test_screen_options_only_high_roc(self, mock_exists, mock_read_csv, mock_ticker):
        # Setup similar to above but guaranteed High ROC
        mock_exists.return_value = True
        mock_read_csv.return_value = pd.DataFrame({'Symbol': ['NVDA']})

        mock_tk = MagicMock()
        mock_ticker.return_value = mock_tk

        # Liquidity OK
        mock_tk.history.return_value = pd.DataFrame({
            'Close': [100.0] * 5,
            'Volume': [20_000_000] * 5
        })

        # Safe Earnings
        mock_tk.calendar = {'Earnings Date': [pd.Timestamp(date.today() + timedelta(days=100))]}

        # Expiry OK
        target_date = date.today() + timedelta(days=45)
        mock_tk.options = [target_date.strftime('%Y-%m-%d')]

        # Chain High Credit
        mock_chain = MagicMock()
        puts_data = {
            'strike': [85.0, 90.0, 95.0, 100.0],
            'bid':    [0.5,  2.0,  4.0,   6.0],
            'ask':    [0.6,  2.1,  4.1,   6.1], # Long 85 (Ask 0.6), Short 90 (Bid 2.0)
            'lastPrice': [0.55, 2.05, 4.05, 6.05],
            'impliedVolatility': [0.5]*4
        }
        # Short 90 Put (approx 30 delta).
        # Screener filters OTM (<100).
        # Calculates delta. Finds short strike closest to -0.30 delta.
        # We assume 90 strike will be picked.
        # Credit = 2.0 (Bid) - 0.6 (Ask) = 1.4
        # Width = 5. Risk = 3.6. ROC = 38%

        mock_chain.puts = pd.DataFrame(puts_data)
        mock_tk.option_chain.return_value = mock_chain

        results = screen_options_only_strategy(limit=1)

        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['verdict'], "🟢 GREEN LIGHT")
        # Check logic picked the right strikes
        # Note: logic might pick different strike depending on delta calc mock
        # But 90/85 spread gives high ROC.
        # Ensure result has roc > 20
        self.assertGreater(results[0]['roc'], 20.0)

    @patch('yfinance.Ticker')
    @patch('pandas.read_csv')
    @patch('os.path.exists')
    def test_limit_parameter(self, mock_exists, mock_read_csv, mock_ticker):
        mock_exists.return_value = True
        # Return unique alpha tickers to pass filter (isalpha) and dedup
        # "ABC" + A..Z -> ABCA, ABCB ... length 4, pure alpha
        tickers = [f"ABC{chr(65 + i)}" for i in range(20)]
        mock_read_csv.return_value = pd.DataFrame({'Symbol': tickers})

        # Mock yfinance to fail fast or return None to speed up test logic
        mock_tk = MagicMock()
        mock_ticker.return_value = mock_tk
        mock_tk.history.side_effect = Exception("Skip") # Fail immediately inside worker

        limit_val = 10
        screen_options_only_strategy(limit=limit_val)

        # Verify we didn't process more than limit
        self.assertEqual(mock_ticker.call_count, limit_val)

    @patch('yfinance.Ticker')
    def test_error_handling(self, mock_ticker):
        # Mock Ticker to raise a critical error or 404
        mock_tk = MagicMock()
        mock_ticker.return_value = mock_tk
        mock_tk.history.side_effect = Exception("404 Not Found")

        # Should catch and return None (empty list at end)
        results = screen_options_only_strategy(limit=1)
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
