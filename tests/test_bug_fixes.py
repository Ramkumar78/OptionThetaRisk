import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_quantum_setups
from option_auditor.unified_screener import run_quantum_audit

class TestFixesRepro(unittest.TestCase):

    @patch('option_auditor.screener.fetch_batch_data_safe')
    @patch('option_auditor.screener.get_cached_market_data')
    def test_identity_theft_bug(self, mock_cached, mock_fetch):
        """
        Test Issue 1: Ambiguous flat dataframe from batch fetch.
        If we request multiple tickers but get a flat dataframe, it should be handled safely.
        The fix should verify we skip or handle it without crashing or misattributing data.
        """
        mock_cached.return_value = pd.DataFrame() # No cache

        # Create a flat dataframe (simulating single ticker result for multiple ticker request)
        dates = pd.date_range(start='2023-01-01', periods=250)
        data = {
            'Open': np.random.rand(250) * 100,
            'High': np.random.rand(250) * 105,
            'Low': np.random.rand(250) * 95,
            'Close': np.random.rand(250) * 100,
            'Volume': np.random.randint(1000, 10000, 250)
        }
        flat_df = pd.DataFrame(data, index=dates)

        mock_fetch.return_value = flat_df

        # Request 2 tickers
        tickers = ["AAPL", "GOOG"]

        # Run screener
        # With the bug, this might crash or assign data to one/both.
        # With the fix, it should return [] and log warning.
        results = screen_quantum_setups(ticker_list=tickers)

        # We expect empty results for this ambiguous case (based on the fix description)
        self.assertEqual(results, [])

    def test_quantum_audit_structure(self):
        """
        Test Issue 4: Verify run_quantum_audit returns correct keys and logic.
        """
        # Mock inputs
        df = pd.DataFrame({
            'Close': np.random.rand(100) * 100
        })
        tech_result = {"master_verdict": "WAIT"}

        # Run audit
        result = run_quantum_audit("TEST", df, tech_result)

        # Check keys
        self.assertIn("quantum_note", result, "Missing 'quantum_note' in result (Fix #4 requirement)")
        self.assertIn("hurst", result)
        self.assertIn("entropy", result)

if __name__ == '__main__':
    unittest.main()
