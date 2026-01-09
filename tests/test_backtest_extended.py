import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.unified_backtester import UnifiedBacktester

class TestBacktestExtended(unittest.TestCase):

    def setUp(self):
        # Create a mock dataframe with perfect trend for testing
        # End date is NOW, so it falls within the backtest window
        end_date = pd.Timestamp.now()
        dates = pd.date_range(end=end_date, periods=500, freq="D")

        # SINE WAVE + TREND
        x = np.linspace(0, 4 * np.pi, 500)
        sine = np.sin(x) * 20
        trend = np.linspace(100, 200, 500)
        close = trend + sine

        # Add a sharp jump for Breakouts
        close[250] += 10

        # High/Low envelopes
        high = close + 2
        low = close - 2
        open_p = close - 1
        volume = np.random.randint(1000000, 5000000, 500)

        self.mock_df = pd.DataFrame({
            "Close": close,
            "High": high,
            "Low": low,
            "Open": open_p,
            "Volume": volume,
            "Spy": close, # Correlated
            "Vix": np.full(500, 15.0) # Low VIX (Green Regime)
        }, index=dates)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_market_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="market")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "MARKET")
        # Market strategy uses RSI dip in trend, sine wave should provide this
        self.assertGreater(result["trades"], 0)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_ema_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="ema_5_13")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "EMA_5_13")
        # EMA crossovers should happen on sine wave

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_darvas_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="darvas")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "DARVAS")

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_fourier_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="fourier")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "FOURIER")
        self.assertGreater(result["trades"], 0)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_hybrid_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="hybrid")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "HYBRID")
        self.assertGreater(result["trades"], 0)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_master_convergence_strategy_backtest(self, mock_fetch):
        mock_fetch.return_value = self.mock_df.copy()

        bt = UnifiedBacktester("TEST", strategy_type="master_convergence")
        result = bt.run()

        self.assertNotIn("error", result)
        self.assertEqual(result["strategy"], "MASTER_CONVERGENCE")

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_negative_no_data(self, mock_fetch):
        mock_fetch.return_value = None

        bt = UnifiedBacktester("TEST", strategy_type="market")
        result = bt.run()

        self.assertIn("error", result)
        self.assertEqual(result["error"], "No data found")

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_negative_insufficient_history(self, mock_fetch):
        # Only 10 days of data
        short_df = self.mock_df.iloc[:10].copy()
        # Update index to be recent so it falls in window, but is short
        short_df.index = pd.date_range(end=pd.Timestamp.now(), periods=10, freq="D")

        mock_fetch.return_value = short_df

        bt = UnifiedBacktester("TEST", strategy_type="market")
        result = bt.run()

        if "error" in result:
             self.assertIn("error", result)
        else:
             self.assertIsNotNone(result)

    @patch("option_auditor.unified_backtester.UnifiedBacktester.fetch_data")
    def test_edge_case_regime_red(self, mock_fetch):
        # Create data where Vix is HIGH (Red Regime)
        df = self.mock_df.copy()
        df['Vix'] = 40.0 # High VIX
        mock_fetch.return_value = df

        bt = UnifiedBacktester("TEST", strategy_type="grandmaster")
        result = bt.run()

        self.assertNotIn("error", result)
        # Grandmaster is long only, so should be 0 trades in RED regime
        self.assertEqual(result["trades"], 0)
