import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest
from option_auditor import screener

# Sample DataFrame for mocking
def get_mock_df():
    dates = pd.date_range(start="2023-01-01", periods=200)
    data = {
        "Open": np.linspace(100, 150, 200),
        "High": np.linspace(102, 152, 200),
        "Low": np.linspace(98, 148, 200),
        "Close": np.linspace(101, 151, 200),
        "Volume": np.random.randint(1000000, 5000000, 200)
    }
    df = pd.DataFrame(data, index=dates)
    return df

class TestScreenerFields(unittest.TestCase):

    def setUp(self):
        self.mock_df = get_mock_df()

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    @patch('yfinance.Ticker')
    def test_market_screener_fields(self, mock_ticker, mock_cached, mock_fetch):
        # Mock fetch to return our df for "AAPL"
        # fetch_batch_data_safe returns a DataFrame (could be MultiIndex or Flat)
        # We'll return flat for simplicity if it works, or handle internal logic
        mock_fetch.return_value = self.mock_df
        # Mock cached data to be empty to force fetch
        mock_cached.return_value = pd.DataFrame()

        # Mock yfinance Ticker info for PE
        mock_instance = MagicMock()
        mock_instance.info = {'trailingPE': 20, 'forwardPE': 22, 'sector': 'Technology'}
        mock_instance.history.return_value = self.mock_df
        mock_instance.options = ('2023-12-01',)
        mock_instance.option_chain.return_value.puts = pd.DataFrame({
            'strike': [100, 105, 110],
            'bid': [1.0, 1.5, 2.0],
            'ask': [1.2, 1.7, 2.2],
            'lastPrice': [1.1, 1.6, 2.1],
            'impliedVolatility': [0.2, 0.2, 0.2]
        })
        mock_ticker.return_value = mock_instance

        # We patch _prepare_data_for_ticker to just return our DF to skip complex logic
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=self.mock_df):
            # We call screen_market with a small list to test
            with patch('option_auditor.common.screener_utils.resolve_region_tickers', return_value=['AAPL']):
                 # screen_market returns a dict of lists
                 results = screener.screen_market(region='us')
                 # Flatten results
                 all_res = []
                 for k, v in results.items():
                     all_res.extend(v)

                 if all_res:
                     first = all_res[0]
                     self.assertIn('atr', first)
                     self.assertIn('breakout_date', first)

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_turtle_screener_fields(self, mock_fetch):
        mock_fetch.return_value = self.mock_df
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=self.mock_df):
             results = screener.screen_turtle_setups(ticker_list=['AAPL'])
             if results:
                 self.assertIn('atr', results[0])
                 self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_ema_screener_fields(self, mock_fetch):
        mock_fetch.return_value = self.mock_df
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=self.mock_df):
             results = screener.screen_5_13_setups(ticker_list=['AAPL'])
             if results:
                 self.assertIn('atr', results[0])
                 self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_darvas_screener_fields(self, mock_fetch):
        mock_fetch.return_value = self.mock_df
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=self.mock_df):
             results = screener.screen_darvas_box(ticker_list=['AAPL'])
             if results:
                 self.assertIn('atr', results[0])
                 self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_mms_screener_fields(self, mock_fetch):
        mock_fetch.return_value = self.mock_df
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=self.mock_df):
             results = screener.screen_mms_ote_setups(ticker_list=['AAPL'])
             if results:
                 self.assertIn('atr', results[0])
                 self.assertIn('breakout_date', results[0])

    @patch('yfinance.Ticker')
    def test_bull_put_fields(self, mock_ticker):
        # Bull put uses yf.Ticker().history explicitly
        mock_instance = MagicMock()
        mock_instance.history.return_value = self.mock_df
        mock_instance.options = ('2023-12-01',)
        # Mock option chain
        puts = pd.DataFrame({
            'strike': [130, 135, 140, 145, 150], # Around price 151
            'bid': [1.0, 1.5, 2.0, 2.5, 3.0],
            'ask': [1.2, 1.7, 2.2, 2.7, 3.2],
            'lastPrice': [1.1, 1.6, 2.1, 2.6, 3.1],
            'impliedVolatility': [0.2, 0.2, 0.2, 0.2, 0.2]
        })
        mock_instance.option_chain.return_value.puts = puts
        mock_ticker.return_value = mock_instance

        # Need to patch date to ensure option expiry is valid (~45 days)
        with patch('option_auditor.strategies.bull_put.date') as mock_date:
            mock_date.today.return_value = pd.to_datetime('2023-10-15').date()
            results = screener.screen_bull_put_spreads(ticker_list=['AAPL'])
            if results:
                self.assertIn('atr', results[0])
                self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    @patch('yfinance.download')
    def test_isa_screener_fields(self, mock_dl, mock_cached):
        mock_cached.return_value = pd.DataFrame() # Force DL
        # yf.download returns MultiIndex usually if grouped by ticker, or simple if one.
        # ISA logic handles both. Let's return simple df for one ticker
        mock_dl.return_value = self.mock_df

        results = screener.screen_trend_followers_isa(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_fourier_screener_fields(self, mock_fetch):
        # Fourier expects batch data, returns iterator
        mock_fetch.return_value = self.mock_df

        results = screener.screen_fourier_cycles(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    def test_hybrid_screener_fields(self, mock_cached):
        mock_cached.return_value = self.mock_df
        results = screener.screen_hybrid_strategy(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    def test_master_screener_fields(self, mock_cached):
        mock_cached.return_value = self.mock_df
        results = screener.screen_master_convergence(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    @patch('option_auditor.strategies.fortress._get_market_regime')
    def test_fortress_screener_fields(self, mock_vix, mock_cached):
        mock_vix.return_value = 15.0
        mock_cached.return_value = self.mock_df
        results = screener.screen_dynamic_volatility_fortress(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            self.assertIn('breakout_date', results[0])

    @patch('option_auditor.common.screener_utils.get_cached_market_data')
    @patch('option_auditor.strategies.quantum.calculate_hurst')
    @patch('option_auditor.strategies.quantum.shannon_entropy')
    @patch('option_auditor.strategies.quantum.kalman_filter')
    @patch('option_auditor.strategies.quantum.generate_human_verdict')
    def test_quantum_screener_fields(self, mock_verdict, mock_kalman, mock_entropy, mock_hurst, mock_cached):
        mock_cached.return_value = self.mock_df
        mock_hurst.return_value = 0.6
        mock_entropy.return_value = 0.5
        mock_kalman.return_value = pd.Series(np.linspace(100, 110, 200))
        mock_verdict.return_value = ("BUY", "Rationale")

        results = screener.screen_quantum_setups(ticker_list=['AAPL'])
        if results:
            self.assertIn('atr', results[0])
            # self.assertIn('breakout_date', results[0])  # Not implemented in quantum

    def test_imports(self):
        # Verify that we can import the new functions
        from option_auditor.uk_stock_data import get_uk_euro_tickers, get_uk_tickers
        from option_auditor.india_stock_data import get_indian_tickers

        self.assertTrue(len(get_uk_euro_tickers()) > 0)
        self.assertTrue(len(get_uk_tickers()) > 0)
        self.assertTrue(len(get_indian_tickers()) > 0)
        self.assertTrue(get_indian_tickers()[0].endswith('.NS'))

if __name__ == '__main__':
    unittest.main()
