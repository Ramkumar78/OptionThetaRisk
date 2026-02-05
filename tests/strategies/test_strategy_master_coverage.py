import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.strategies.master import FortressMasterScreener

class TestFortressMasterScreenerCoverage(unittest.TestCase):
    def setUp(self):
        self.mock_regime = {
            "regime": "NEUTRAL",
            "spy_history": None,
            "vix": 20.0
        }
        self.screener = FortressMasterScreener(self.mock_regime, check_mode=False)

    def test_analyze_uk_liquidity_fail(self):
        # UK stock, low turnover
        dates = pd.date_range("2023-01-01", periods=300)
        df = pd.DataFrame({
            "Close": [100]*300, # 100 pence = 1 GBP
            "Volume": [1000]*300 # Turnover = 1 * 1000 = 1000 GBP. Likely too low.
        }, index=dates)

        result = self.screener.analyze("TEST.L", df)
        self.assertIsNone(result)

    def test_analyze_india_liquidity_fail(self):
        dates = pd.date_range("2023-01-01", periods=300)
        df = pd.DataFrame({
            "Close": [50]*300,
            "Volume": [100]*300
        }, index=dates)

        result = self.screener.analyze("TEST.NS", df)
        self.assertIsNone(result)

    def test_analyze_options_income_logic(self):
        # US Stock, Neutral/Bullish Regime
        self.screener.regime = "🟢 BULLISH"

        dates = pd.date_range("2023-01-01", periods=300)
        prices = np.linspace(100, 105, 300)
        df = pd.DataFrame({
            "Close": prices,
            "High": prices + 1,
            "Low": prices - 1,
            "Volume": [1000000]*300
        }, index=dates)

        # Mock Grandmaster to NOT return signal so we fall through to options logic
        with patch.object(self.screener.grandmaster, 'analyze') as mock_gm:
            mock_gm.return_value = {"signal": "WAIT"}

            # Need RSI < 45 and > 30 for Bull Put
            # We mock pandas_ta.rsi
            with patch('option_auditor.strategies.master.ta.rsi') as mock_rsi:
                mock_rsi.return_value = pd.Series([40]*300)

                result = self.screener.analyze("AAPL", df)

                self.assertIsNotNone(result)
                self.assertIn("BULL PUT", result["Setup"])

    def test_rs_score_no_history(self):
        # spy_history is None
        self.screener.spy_history = None
        df = pd.DataFrame({"Close": [100]}, index=[pd.Timestamp("2023-01-01")])
        score = self.screener._calculate_rs_score(df)
        self.assertEqual(score, 0)

    def test_rs_score_short_history(self):
        # spy_history exists but short intersection
        dates = pd.date_range("2023-01-01", periods=10)
        self.screener.spy_history = pd.Series(range(10), index=dates)

        df = pd.DataFrame({"Close": range(10)}, index=dates)
        score = self.screener._calculate_rs_score(df)
        self.assertEqual(score, 0)

    def test_analyze_exception_handling(self):
        # Force exception
        self.screener.grandmaster = MagicMock()
        self.screener.grandmaster.analyze.side_effect = Exception("Boom")

        dates = pd.date_range("2023-01-01", periods=300)
        df = pd.DataFrame({"Close": [100]*300}, index=dates)

        result = self.screener.analyze("AAPL", df)
        self.assertIsNone(result)
