import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.master_screener import FortressScreener, screen_master_convergence

class TestFortressScreener(unittest.TestCase):
    def setUp(self):
        self.us_tickers = ["AAPL", "NVDA", "SPY"]
        self.uk_tickers = ["RR.L", "BARC.L"]
        self.screener = FortressScreener(self.us_tickers, self.uk_tickers)

    @patch("option_auditor.master_screener.yf.download")
    def test_fetch_market_regime_bullish(self, mock_download):
        # Mock SPY and VIX data for Bullish Regime
        # SPY > 200 SMA, VIX < 20
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        spy_prices = np.linspace(300, 500, 300) # Uptrend
        vix_prices = np.full(300, 15.0) # Low VIX

        data = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns) # Ensure MultiIndex

        mock_download.return_value = data

        self.screener._fetch_market_regime()
        self.assertIn("BULLISH", self.screener.regime)
        self.assertIsNotNone(self.screener.spy_history)

    @patch("option_auditor.master_screener.yf.download")
    def test_fetch_market_regime_bearish(self, mock_download):
        # Mock SPY and VIX data for Bearish Regime
        # SPY < 200 SMA
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        spy_prices = np.linspace(500, 300, 300) # Downtrend
        vix_prices = np.full(300, 25.0) # High VIX

        data = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices
        }, index=dates)
        data.columns = pd.MultiIndex.from_tuples(data.columns)

        mock_download.return_value = data

        self.screener._fetch_market_regime()
        self.assertIn("BEARISH", self.screener.regime)

    def test_calculate_rs_score(self):
        # Setup mock spy history
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
        spy_hist = pd.Series(np.linspace(100, 110, 100), index=dates) # +10%
        self.screener.spy_history = spy_hist

        # Stock outperforms: +20%
        stock_df = pd.DataFrame({
            'Close': np.linspace(100, 120, 100)
        }, index=dates)

        rs_score = self.screener._calculate_rs_score(stock_df)
        self.assertGreater(rs_score, 0)

        # Stock underperforms: +5%
        stock_df_weak = pd.DataFrame({
            'Close': np.linspace(100, 105, 100)
        }, index=dates)
        rs_score_weak = self.screener._calculate_rs_score(stock_df_weak)
        self.assertLess(rs_score_weak, 0)

    @patch("option_auditor.master_screener.yf.download")
    def test_run_screen_isa_vcp(self, mock_download):
        # 1. Setup Market Regime (Bullish)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        spy_prices = np.linspace(400, 500, 300)
        vix_prices = np.full(300, 15.0)

        market_data = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices
        }, index=dates)
        market_data.columns = pd.MultiIndex.from_tuples(market_data.columns)

        # 2. Setup Stock Data (ISA VCP Candidate)
        # Strong uptrend: 100 -> 200
        trend_phase = np.linspace(100, 200, 250)

        # Consolidation Phase (VCP): Last 50 bars
        # Make sure price stays above SMAs.
        # SMA 50 will be approx average of last 50.
        # If we keep price steady at 200, SMA 50 will slowly approach 200.
        # To ensure Price > SMA 50, we should have the price drift slightly higher or stay at peak while SMA catches up from below.
        # In the previous test, noise might have pushed last price below 200.

        consolidation_phase = np.full(50, 205.0) # slightly higher than peak of trend to ensure above SMA

        # Inject Volatility
        rng = np.random.default_rng(42)
        noise_high = rng.normal(0, 2.0, 25)
        noise_low = rng.normal(0, 0.5, 25)

        consolidation_phase[:25] += noise_high
        consolidation_phase[25:] += noise_low

        stock_prices = np.concatenate([trend_phase, consolidation_phase])
        stock_volume = np.full(300, 1_000_000) # Liquid

        stock_df = pd.DataFrame({
            'Close': stock_prices,
            'High': stock_prices + 2,
            'Low': stock_prices - 2,
            'Volume': stock_volume
        }, index=dates)
        # Add index name
        stock_df.index.name = "Date"

        # Manually set regime
        self.screener.regime = "🟢 BULLISH"
        self.screener.spy_history = market_data['Close']['SPY']

        # Also need to ensure RS Rating > 0.
        # SPY went 400 -> 500 (+25%).
        # Stock went 100 -> 205 (+105%).
        # RS should be positive.

        result = self.screener._analyze_ticker("NVDA", stock_df)

        if result is None:
             # Debug
             close = stock_df['Close']
             sma_50 = float(close.rolling(50).mean().iloc[-1])
             curr = float(close.iloc[-1])
             print(f"DEBUG: Price={curr}, SMA50={sma_50}")

        self.assertIsNotNone(result)
        self.assertIn("ISA: VCP LEADER", result['Setup'])
        self.assertEqual(result['VCP'], "YES")
        self.assertIn("BUY", result['Action'])

    def test_analyze_ticker_liquidity_fail(self):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        # Low volume
        stock_df = pd.DataFrame({
            'Close': np.full(300, 100.0),
            'High': np.full(300, 101.0),
            'Low': np.full(300, 99.0),
            'Volume': np.full(300, 1000) # Very low volume
        }, index=dates)

        result = self.screener._analyze_ticker("TEST", stock_df)
        self.assertIsNone(result)

    def test_screen_master_convergence_adapter(self):
        # Test the wrapper function
        # Mock FortressScreener.run_screen
        with patch("option_auditor.master_screener.FortressScreener.run_screen") as mock_run:
            mock_run.return_value = [{"Ticker": "AAPL", "Score": 95}]

            # Case 1: Default US
            results = screen_master_convergence(region="us")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['Ticker'], "AAPL")

            # Case 2: Custom List
            results_custom = screen_master_convergence(ticker_list=["MSFT"])
            self.assertEqual(len(results_custom), 1)

if __name__ == '__main__':
    unittest.main()
