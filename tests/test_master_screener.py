import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.strategies.master import FortressMasterScreener, screen_master_convergence, get_detailed_market_regime

class TestFortressMasterScreener(unittest.TestCase):
    def setUp(self):
        self.mock_regime = {
            "regime": "NEUTRAL",
            "spy_history": None,
            "vix": 20.0
        }
        self.screener = FortressMasterScreener(self.mock_regime, check_mode=True)

    @patch("option_auditor.strategies.master.yf.download")
    def test_get_detailed_market_regime_bullish(self, mock_download):
        # Mock SPY and VIX data for Bullish Regime
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        spy_prices = np.linspace(300, 500, 300) # Uptrend
        vix_prices = np.full(300, 15.0) # Low VIX

        data = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)

        mock_download.return_value = data

        regime_data = get_detailed_market_regime()
        self.assertIn("BULLISH", regime_data["regime"])
        self.assertIsNotNone(regime_data["spy_history"])

    @patch("option_auditor.strategies.master.yf.download")
    def test_get_detailed_market_regime_bearish(self, mock_download):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        spy_prices = np.linspace(500, 300, 300) # Downtrend
        vix_prices = np.full(300, 25.0) # High VIX

        data = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)

        mock_download.return_value = data

        regime_data = get_detailed_market_regime()
        self.assertIn("BEARISH", regime_data["regime"])

    def test_calculate_rs_score(self):
        # Setup mock spy history in screener
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
        spy_hist = pd.Series(np.linspace(100, 110, 100), index=dates)

        self.screener.spy_history = spy_hist

        stock_df = pd.DataFrame({
            'Close': np.linspace(100, 120, 100)
        }, index=dates)

        rs_score = self.screener._calculate_rs_score(stock_df)
        self.assertGreater(rs_score, 0)

    def test_analyze_ticker_growth(self):
        # 1. Setup Regime
        self.screener.regime = "🟢 BULLISH"

        # 2. Setup Stock Data (Breakout)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)

        # Create a breakout pattern: Flat then pop
        prices = np.concatenate([np.full(250, 100.0), np.linspace(100, 110, 50)])

        # Ensure it passes trend checks (SMA200 < Price)
        # SMA200 of first 200 is 100.
        # Price 110.

        # Donchian High needs to be broken.
        # Max of last 20 was 100 (until the pop).
        # Pop goes to 110. Breakout!

        # Grandmaster uses Donchian High 20 (shifted 1).

        stock_df = pd.DataFrame({
            'Close': prices,
            'High': prices + 1,
            'Low': prices - 1,
            'Volume': np.full(300, 1_000_000)
        }, index=dates)

        # Mock Grandmaster analyze to return BUY signal
        # Or rely on real logic. Grandmaster uses TA lib or manual.
        # Let's rely on real logic if possible, or mock if too complex.
        # Real logic uses indicators.

        # For simplicity in this unit test, let's assume Grandmaster returns a BUY signal
        # via mocking, to test the Orchestrator logic specifically.

        with patch.object(self.screener.grandmaster, 'analyze') as mock_gm:
            mock_gm.return_value = {
                "signal": "BUY",
                "volatility_atr": 2.0,
                "breakout_level": 105.0,
                "stop_loss_atr": 105.0 # Trailing stop
            }

            result = self.screener.analyze("AAPL", stock_df)

            self.assertIsNotNone(result)
            self.assertIn("Breakout", result['Setup'])
            self.assertIn("BUY", result['Action'])

    def test_analyze_ticker_liquidity_fail(self):
        # Disable check_mode to enforce liquidity
        self.screener.check_mode = False

        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        stock_df = pd.DataFrame({
            'Close': np.full(300, 100.0),
            'High': np.full(300, 101.0),
            'Low': np.full(300, 99.0),
            'Volume': np.full(300, 1000) # Low volume
        }, index=dates)

        result = self.screener.analyze("TEST", stock_df)
        self.assertIsNone(result)

    @patch("option_auditor.strategies.master.get_detailed_market_regime")
    @patch("option_auditor.strategies.master.ScreeningRunner")
    def test_screen_master_convergence_integration(self, mock_runner_cls, mock_regime):
        # Test the top level function
        mock_regime.return_value = {"regime": "BULLISH", "spy_history": None, "vix": 15}

        mock_runner_instance = mock_runner_cls.return_value
        mock_runner_instance.run.return_value = [{"Ticker": "AAPL", "Score": 95}]

        results = screen_master_convergence(region="us")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['Ticker'], "AAPL")
        mock_regime.assert_called_once()

if __name__ == '__main__':
    unittest.main()
