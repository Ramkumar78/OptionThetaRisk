import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.unified_backtester import UnifiedBacktester

class TestUnifiedBacktesterNew(unittest.TestCase):
    def setUp(self):
        self.ticker = "TEST"
        self.backtester = UnifiedBacktester(self.ticker)

    @patch('option_auditor.unified_backtester.yf.download')
    def test_backtest_duration_calculation(self, mock_download):
        # Create a date range for 3 years to satisfy data fetching
        dates = pd.date_range(end=pd.Timestamp.now(), periods=1000, freq='D')

        # Create mock data
        # Price increasing to trigger buy, then decreasing to trigger sell
        close = np.linspace(100, 200, 1000)
        # Create a dip to trigger exit
        close[-10:] = 100

        data = pd.DataFrame({
            'Close': close,
            'High': close + 5,
            'Low': close - 5,
            'Open': close, # Simplified
            'Volume': np.ones(1000) * 1000000
        }, index=dates)

        # Create MultiIndex columns as expected by the new yf
        columns = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Open', 'Volume'], [self.ticker, 'SPY', '^VIX']])
        # Just replicate data for all columns for simplicity
        mock_df = pd.DataFrame(np.tile(data.values, (1, 3)), index=dates, columns=columns)

        mock_download.return_value = mock_df

        # Run backtester
        result = self.backtester.run()

        # Verify keys in result
        self.assertIn('buy_hold_days', result)
        self.assertIn('avg_days_held', result)
        self.assertIn('log', result)

        # Verify buy_hold_days logic (approx 2 years = 730 days)
        # Since we simulate data for 2 years window inside run(), check if it's close to 730
        # The backtester slices data for last 730 days.
        # It calculates days between first and last index of sliced data.
        self.assertTrue(result['buy_hold_days'] >= 728)

        # Verify trade log has 'days' field
        if result['log']:
            for trade in result['log']:
                self.assertIn('days', trade)
                if trade['type'] == 'SELL':
                     self.assertIsInstance(trade['days'], int)

    @patch('option_auditor.unified_backtester.yf.download')
    def test_backtest_avg_days_held(self, mock_download):
         # Create mock data
        dates = pd.date_range(end=pd.Timestamp.now(), periods=1000, freq='D')

        # Reuse setup from previous test
        close = np.linspace(100, 200, 1000)
        data = pd.DataFrame({
            'Close': close,
            'High': close + 5,
            'Low': close - 5,
            'Open': close,
            'Volume': np.ones(1000) * 1000000
        }, index=dates)
        columns = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Open', 'Volume'], [self.ticker, 'SPY', '^VIX']])
        mock_df = pd.DataFrame(np.tile(data.values, (1, 3)), index=dates, columns=columns)
        mock_download.return_value = mock_df

        result = self.backtester.run()

        self.assertIsInstance(result['avg_days_held'], int)
        self.assertIsInstance(result['buy_hold_days'], int)

if __name__ == '__main__':
    unittest.main()
