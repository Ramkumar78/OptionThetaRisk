import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.master_backtester import MasterBacktester
from datetime import datetime, timedelta

class TestMasterBacktester(unittest.TestCase):
    def setUp(self):
        self.ticker = "NVDA"
        self.backtester = MasterBacktester(self.ticker)

    @patch('option_auditor.master_backtester.yf.download')
    def test_fetch_data_success(self, mock_download):
        # Create a mock DataFrame that mimics yfinance output
        # Columns: (PriceType, Ticker)
        dates = pd.date_range(start="2020-01-01", periods=100)
        tickers = ["NVDA", "SPY", "^VIX"]

        # Create MultiIndex columns
        cols = pd.MultiIndex.from_product([['Close', 'High', 'Low', 'Volume'], tickers])

        data = pd.DataFrame(np.random.rand(100, 12), index=dates, columns=cols)
        # Ensure 'Close' is accessed correctly in fetch_data

        mock_download.return_value = data

        df = self.backtester.fetch_data()

        self.assertIsNotNone(df)
        self.assertIn('close', df.columns)
        self.assertIn('spy', df.columns)
        self.assertIn('vix', df.columns)
        self.assertEqual(len(df), 100)

    @patch('option_auditor.master_backtester.yf.download')
    def test_fetch_data_failure(self, mock_download):
        mock_download.side_effect = Exception("Download failed")
        df = self.backtester.fetch_data()
        self.assertIsNone(df)

    def test_calculate_indicators(self):
        # Create dummy data
        dates = pd.date_range(start="2020-01-01", periods=300)
        df = pd.DataFrame({
            'close': np.linspace(100, 200, 300),
            'high': np.linspace(101, 201, 300),
            'low': np.linspace(99, 199, 300),
            'spy': np.linspace(300, 400, 300),
            'vix': np.random.uniform(10, 30, 300)
        }, index=dates)

        df_processed = self.backtester.calculate_indicators(df)

        self.assertIn('spy_sma200', df_processed.columns)
        self.assertIn('sma200', df_processed.columns)
        self.assertIn('atr', df_processed.columns)
        self.assertIn('donchian_high', df_processed.columns)

        # Check that dropna worked (rolling 200 needs 200 periods)
        # 300 - 199 (since rolling window includes current) = 101 approx?
        # Actually dropna removes any row with ANY NaN.
        # SMA200 starts at index 199. Shifted donchian starts at 20.
        # So resulting df should start around index 199.
        self.assertTrue(len(df_processed) < 150)

    @patch('option_auditor.master_backtester.MasterBacktester.fetch_data')
    def test_run_simulation(self, mock_fetch_data):
        # Use dates that cover the last 2 years, because the backtester
        # specifically filters for the last 2 years:
        # start_date = pd.Timestamp.now() - pd.DateOffset(years=2)
        # sim_data = df[df.index >= start_date].copy()

        now = datetime.now()
        start = now - timedelta(days=365*3) # 3 years ago to allow warmup and covering last 2 years
        dates = pd.date_range(start=start, end=now, freq='D')
        n_periods = len(dates)

        # Construct price path
        close_prices = []
        for i in range(n_periods):
            close_prices.append(100.0 + (i * 0.1)) # Constant Uptrend

        df = pd.DataFrame({
            'close': close_prices,
            'high': [c + 1 for c in close_prices],
            'low': [c - 1 for c in close_prices],
            'volume': [1000000] * n_periods,
            'spy': [400] * n_periods, # Always above SMA200
            'vix': [15] * n_periods   # Low VIX
        }, index=dates)

        # Return this DF
        mock_fetch_data.return_value = df

        result = self.backtester.run()

        # We expect trades or at least a valid result structure
        self.assertIn('strategy_return', result)
        self.assertIn('trades', result)
        self.assertEqual(result['ticker'], "NVDA")
        self.assertIsInstance(result['strategy_return'], float)

    def test_empty_data(self):
        with patch('option_auditor.master_backtester.MasterBacktester.fetch_data', return_value=None):
            result = self.backtester.run()
            self.assertIn("error", result)

if __name__ == '__main__':
    unittest.main()
