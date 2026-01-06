import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.master_screener import QuantMasterScreener

class TestQuantMasterScreener(unittest.TestCase):
    def setUp(self):
        self.screener = QuantMasterScreener(use_ibkr=False)

    def test_initialization(self):
        self.assertIsInstance(self.screener, QuantMasterScreener)
        self.assertFalse(self.screener.use_ibkr)
        self.assertTrue(self.screener.results.empty)

    @patch('option_auditor.master_screener.obb')
    def test_fetch_data_openbb(self, mock_obb):
        # Mock the OpenBB response
        mock_df = pd.DataFrame({
            'open': [150.0, 152.0, 153.0],
            'high': [155.0, 156.0, 157.0],
            'low': [149.0, 151.0, 152.0],
            'close': [151.0, 153.0, 155.0],
            'volume': [1000, 1200, 1100]
        })
        # Mock the chain: obb.equity.price.historical(...).to_df() -> mock_df
        mock_obb.equity.price.historical.return_value.to_df.return_value = mock_df

        df = self.screener.fetch_data_openbb("AAPL")
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 3)
        self.assertIn('close', df.columns)

    def test_analyze_statistical_features(self):
        df = pd.DataFrame({
            'close': np.random.normal(100, 5, 100)
        })
        stats = self.screener.analyze_statistical_features(df)
        self.assertIn('annualized_volatility', stats)
        self.assertIn('skewness', stats)
        self.assertIn('kurtosis', stats)

    def test_generate_ml_signal_insufficient_data(self):
        df = pd.DataFrame({'close': [100, 101, 102]}) # Too short
        score = self.screener.generate_ml_signal(df)
        self.assertEqual(score, 0.5)

    def test_generate_ml_signal_sufficient_data(self):
        # Generate a longer dataframe
        dates = pd.date_range(start='2023-01-01', periods=100)
        df = pd.DataFrame({
            'close': np.random.normal(100, 5, 100),
            'volume': np.random.randint(1000, 5000, 100)
        }, index=dates)

        score = self.screener.generate_ml_signal(df)
        self.assertTrue(0.0 <= score <= 1.0)

    @patch('option_auditor.master_screener.QuantMasterScreener.fetch_data_openbb')
    def test_run_screen(self, mock_fetch):
        # Mock fetch to return a valid DF
        dates = pd.date_range(start='2023-01-01', periods=100)
        mock_df = pd.DataFrame({
            'close': np.linspace(100, 120, 100) + np.random.normal(0, 1, 100), # Upward trend
            'volume': np.random.randint(1000, 5000, 100)
        }, index=dates)
        mock_fetch.return_value = mock_df

        results = self.screener.run_screen(["AAPL"])

        # It might return empty if ML score < 0.60, but it shouldn't crash
        self.assertIsInstance(results, pd.DataFrame)
        if not results.empty:
            self.assertIn('ML_Prob_Up', results.columns)
            self.assertIn('Ticker', results.columns)
