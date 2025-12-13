import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import pandas_ta as ta
from option_auditor.screener import _screen_tickers

class TestScreenerIntervals(unittest.TestCase):
    @patch('option_auditor.screener.yf.download')
    def test_screen_tickers_weekly(self, mock_download):
        # Mock Data for Weekly: 2 years of weekly data
        dates = pd.date_range(start='2022-01-01', end='2024-01-01', freq='W-FRI')
        data = {
            ('TEST', 'Open'): [100.0 + i for i in range(len(dates))],
            ('TEST', 'High'): [105.0 + i for i in range(len(dates))],
            ('TEST', 'Low'): [95.0 + i for i in range(len(dates))],
            ('TEST', 'Close'): [102.0 + i for i in range(len(dates))],
            ('TEST', 'Volume'): [1000000 for _ in range(len(dates))]
        }
        # Create MultiIndex DataFrame
        df = pd.DataFrame(data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        # Mock return value
        mock_download.return_value = df

        # Run screener
        results = _screen_tickers(['TEST'], iv_rank_threshold=100, rsi_threshold=100, time_frame='1wk')

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res['ticker'], 'TEST')
        self.assertIsNotNone(res['sma_50'])
        self.assertIsNotNone(res['rsi'])
        # Verify 1D % (which is 1W % for weekly interval logic) is calculated
        self.assertIsNotNone(res['pct_change_1d'])

    @patch('option_auditor.screener.yf.download')
    def test_screen_tickers_monthly(self, mock_download):
        # Mock Data for Monthly: 5 years of monthly data
        # 'ME' alias is not available in pandas < 2.2, use 'M'
        dates = pd.date_range(start='2019-01-01', end='2024-01-01', freq='M')
        data = {
            ('TEST', 'Open'): [100.0 + i for i in range(len(dates))],
            ('TEST', 'High'): [105.0 + i for i in range(len(dates))],
            ('TEST', 'Low'): [95.0 + i for i in range(len(dates))],
            ('TEST', 'Close'): [102.0 + i for i in range(len(dates))],
            ('TEST', 'Volume'): [1000000 for _ in range(len(dates))]
        }
        # Create MultiIndex DataFrame
        df = pd.DataFrame(data, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        # Mock return value
        mock_download.return_value = df

        # Run screener
        results = _screen_tickers(['TEST'], iv_rank_threshold=100, rsi_threshold=100, time_frame='1mo')

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertIsNotNone(res['sma_50'])

if __name__ == '__main__':
    unittest.main()
