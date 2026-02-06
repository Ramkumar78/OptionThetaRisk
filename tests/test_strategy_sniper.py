
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest
from option_auditor import screener
from option_auditor.unified_backtester import UnifiedBacktester

class TestSniperStrategy(unittest.TestCase):

    def setUp(self):
        # Create a sample DataFrame that simulates a trending stock
        dates = pd.date_range(start="2020-01-01", periods=300, freq="D")

        # Create a trend: price increasing
        price = np.linspace(100, 200, 300)
        # Add some noise
        noise = np.random.normal(0, 1, 300)
        close = price + noise

        self.df = pd.DataFrame({
            'Open': close - 1,
            'High': close + 2,
            'Low': close - 2,
            'Close': close,
            'Volume': 1000000
        }, index=dates)

        # Ensure SMA 200 is calculable and price is above it (Uptrend)

        # Modify last row to trigger Alpha > 0.5
        self.df.iloc[-1, self.df.columns.get_loc('Close')] = 200.0
        self.df.iloc[-1, self.df.columns.get_loc('Open')] = 198.0
        self.df.iloc[-1, self.df.columns.get_loc('High')] = 200.5
        self.df.iloc[-1, self.df.columns.get_loc('Low')] = 198.0

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.common.screener_utils.resolve_region_tickers')
    def test_screen_my_strategy_bullish_trigger(self, mock_tickers, mock_fetch):
        mock_tickers.return_value = ['AAPL']
        mock_fetch.return_value = self.df  # Return flat DF for single ticker logic handling or mock MultiIndex

        results = screener.screen_my_strategy(ticker_list=['AAPL'])

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res['ticker'], 'AAPL')
        # Check for 'sniper' (case insensitive)
        self.assertIn('sniper', (res['signal'] + " " + res['verdict']).lower())
        self.assertGreater(res['alpha_101'], 0.5)
        self.assertIn('stop_loss', res)
        self.assertIn('target', res)
        self.assertIn('breakout_level', res)
        self.assertIn('breakout_date', res)
        self.assertIn('atr_value', res)

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_screen_my_strategy_bearish_trend(self, mock_fetch):
        # Create Bearish DF (Price < SMA 200)
        df_bear = self.df.copy()
        # Drop price below SMA200 (which is ~150)
        df_bear.iloc[-1, df_bear.columns.get_loc('Close')] = 100.0
        # Ensure Alpha is still high to isolate trend check
        df_bear.iloc[-1, df_bear.columns.get_loc('Open')] = 90.0

        mock_fetch.return_value = df_bear

        results = screener.screen_my_strategy(ticker_list=['AAPL'])
        self.assertEqual(len(results), 0)

    @patch('option_auditor.backtest_data_loader.yf.download')
    def test_backtest_my_strategy(self, mock_download):
        # Setup mock data for backtester
        # Create a DF with enough history ending TODAY
        end_date = pd.Timestamp.now()
        dates = pd.date_range(end=end_date, periods=2000, freq="D")
        price = np.linspace(100, 200, 2000)
        close = price

        tuples = []
        for col in ['Close', 'High', 'Low', 'Open', 'Volume']:
            for tick in ['AAPL', 'SPY', '^VIX']:
                tuples.append((col, tick))

        cols = pd.MultiIndex.from_tuples(tuples)
        data = pd.DataFrame(np.random.randn(2000, 15), index=dates, columns=cols)

        # Fix values to be positive and sensible
        for tick in ['AAPL', 'SPY']:
            data[('Close', tick)] = close
            data[('Open', tick)] = close - 1
            data[('High', tick)] = close + 2
            data[('Low', tick)] = close - 2
            data[('Volume', tick)] = 1000000

        data[('Close', '^VIX')] = 15.0 # Low Volatility

        # Trigger condition at index -10:
        # Trend is Up (since price increasing linearly)
        # Alpha 101 > 0.5
        idx = -10
        # Price at idx -10 is approx 199. Keep it high to stay above SMA.
        data.loc[dates[idx], ('Close', 'AAPL')] = 200.0
        data.loc[dates[idx], ('Open', 'AAPL')] = 198.0
        data.loc[dates[idx], ('High', 'AAPL')] = 201.0
        data.loc[dates[idx], ('Low', 'AAPL')] = 198.0

        # Force Exit (Target Hit) at index -5
        idx_exit = -5
        data.loc[dates[idx_exit], ('Close', 'AAPL')] = 220.0
        data.loc[dates[idx_exit], ('High', 'AAPL')] = 225.0

        # Verify Alpha
        c = data.loc[dates[idx], ('Close', 'AAPL')]
        o = data.loc[dates[idx], ('Open', 'AAPL')]
        h = data.loc[dates[idx], ('High', 'AAPL')]
        l = data.loc[dates[idx], ('Low', 'AAPL')]
        alpha = (c - o) / ((h - l) + 0.001)
        print(f"DEBUG: Alpha at {dates[idx]}: {alpha}")

        mock_download.return_value = data

        # Disable mock data mode to ensure we use the mocked yfinance data
        with patch.dict('os.environ', {'CI': 'false', 'USE_MOCK_DATA': 'false'}):
            bt = UnifiedBacktester("AAPL", strategy_type="mystrategy")
            result = bt.run()

        if 'error' in result:
             self.fail(f"Backtest returned error: {result['error']}")

        self.assertEqual(result['ticker'], 'AAPL')
        # Check if any trade happened
        self.assertGreater(result['trades'], 0)
        self.assertIn('strategy_return', result)

    def test_screen_my_strategy_edge_cases(self):
        # Empty Data
        with patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_fetch, \
             patch('option_auditor.common.data_utils.fetch_data_with_retry') as mock_retry_fetch:

            mock_fetch.return_value = pd.DataFrame()
            mock_retry_fetch.return_value = pd.DataFrame()

            results = screener.screen_my_strategy(ticker_list=['AAPL'])
            self.assertEqual(results, [])

        # Short Data (Not enough for SMA 200)
        with patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_fetch:
            short_df = self.df.iloc[-100:]
            mock_fetch.return_value = short_df
            results = screener.screen_my_strategy(ticker_list=['AAPL'])
            self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
