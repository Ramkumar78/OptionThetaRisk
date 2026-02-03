import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor import portfolio_risk

class TestPortfolioGreeks(unittest.TestCase):

    def setUp(self):
        # Use a future date for expiry to ensure T > 0
        future_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

        self.positions = [
            {'ticker': 'NVDA', 'type': 'call', 'strike': 100, 'expiry': future_date, 'qty': 1},
            {'ticker': 'SPY', 'type': 'put', 'strike': 400, 'expiry': future_date, 'qty': 1}
        ]

    @patch('option_auditor.portfolio_risk.get_cached_market_data')
    def test_analyze_portfolio_greeks(self, mock_get_data):
        # Mock Data
        dates = pd.date_range(start='2024-01-01', periods=100)
        # NVDA trend up -> Returns positive
        nvda_close = np.linspace(100, 110, 100)
        spy_close = np.linspace(400, 410, 100)

        data_dict = {
            ('NVDA', 'Close'): nvda_close,
            ('SPY', 'Close'): spy_close
        }
        mock_df = pd.DataFrame(data_dict, index=dates)
        mock_get_data.return_value = mock_df

        # Current Price should be last value (110, 410)
        # Vol will be calculated from log returns.

        result = portfolio_risk.analyze_portfolio_greeks(self.positions)

        self.assertIn('portfolio_totals', result)
        totals = result['portfolio_totals']

        # We assume result has totals
        self.assertIsInstance(totals['delta'], float)
        self.assertIsInstance(totals['gamma'], float)
        self.assertIsInstance(totals['theta'], float)
        self.assertIsInstance(totals['vega'], float)

        # Check Positions
        positions = result['positions']
        self.assertEqual(len(positions), 2)

        nvda_pos = next(p for p in positions if p['ticker'] == 'NVDA')
        self.assertEqual(nvda_pos['S'], 110.0)
        self.assertTrue(nvda_pos['delta'] > 0) # Call

        spy_pos = next(p for p in positions if p['ticker'] == 'SPY')
        self.assertEqual(spy_pos['S'], 410.0)
        self.assertTrue(spy_pos['delta'] < 0, f"Expected Delta < 0 for Put, got {spy_pos['delta']}") # Put

    @patch('option_auditor.portfolio_risk.get_cached_market_data')
    def test_missing_data_greeks(self, mock_get_data):
        mock_get_data.return_value = pd.DataFrame() # No data

        result = portfolio_risk.analyze_portfolio_greeks(self.positions)

        positions = result['positions']
        self.assertEqual(len(positions), 2)
        self.assertIn('error', positions[0])
        self.assertEqual(positions[0]['error'], 'Price unavailable')

if __name__ == '__main__':
    unittest.main()
