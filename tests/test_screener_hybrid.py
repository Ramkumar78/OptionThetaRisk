import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy

class TestScreenerHybrid(unittest.TestCase):

    # Patching where ScreeningRunner calls it
    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.hybrid.get_cached_market_data')
    @patch('option_auditor.common.screener_utils.SECTOR_COMPONENTS', {"WATCH": ["AAPL"]})
    def test_screen_hybrid_strategy_bullish_bottom(self, mock_cache, mock_fetch):
        """Test Scenario A: Bullish Trend + Cycle Bottom"""
        dates = pd.date_range(end='2023-01-01', periods=500)
        opens = np.linspace(100, 200, 500)
        opens[-1] = 199.0

        df = pd.DataFrame({
            'Close': np.linspace(100, 200, 500),
            'High': np.linspace(105, 205, 500),
            'Low': np.linspace(95, 195, 500),
            'Open': opens,
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        # Mock cache to return the data directly
        mock_cache.return_value = df
        mock_fetch.return_value = pd.DataFrame()

        with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle') as mock_cycle:
            mock_cycle.return_value = (20.0, -0.9)

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['ticker'], "TEST")
            self.assertEqual(r['score'], 95)


    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.hybrid.get_cached_market_data')
    def test_screen_hybrid_strategy_bearish_top(self, mock_cache, mock_fetch):
        """Test Scenario C: Bearish Trend + Cycle Top"""
        dates = pd.date_range(end='2023-01-01', periods=500)

        df = pd.DataFrame({
            'Close': np.linspace(200, 100, 500),
            'High': np.linspace(205, 105, 500),
            'Low': np.linspace(195, 95, 500),
            'Open': np.linspace(200, 100, 500),
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        mock_cache.return_value = df

        with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle') as mock_cycle:
            mock_cycle.return_value = (20.0, 0.8)

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['trend'], "BEARISH")
            self.assertIn("TOP", r['cycle'])

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.hybrid.get_cached_market_data')
    def test_screen_hybrid_strategy_momentum_buy(self, mock_cache, mock_fetch):
        """Test Scenario B: Bullish + Breakout (High > 50d High)"""
        dates = pd.date_range(end='2023-01-01', periods=500)
        closes = np.linspace(100, 200, 500)
        closes[-1] = 210
        highs = np.linspace(105, 205, 500)

        df = pd.DataFrame({
            'Close': closes,
            'High': highs,
            'Low': np.linspace(95, 195, 500),
            'Open': np.linspace(100, 200, 500),
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        mock_cache.return_value = df

        with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle') as mock_cycle:
            mock_cycle.return_value = (20.0, 0.0)

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['trend'], "BULLISH")
            self.assertIn("BREAKOUT BUY", r['verdict'])

    def create_mock_df(self, closes, volume=1000000):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=len(closes))
        df = pd.DataFrame({
            'Open': closes,
            'High': [c * 1.01 for c in closes],
            'Low': [c * 0.99 for c in closes],
            'Close': closes,
            'Volume': [volume] * len(closes)
        }, index=dates)
        return df

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    @patch('option_auditor.strategies.hybrid.get_cached_market_data')
    @patch('yfinance.download')
    def test_hybrid_volume_filtering(self, mock_yf_download, mock_get_cached, mock_fetch_batch):
        """Test volume filtering logic (Liquid vs Illiquid vs Watchlist)"""
        tickers = ["LIQUID", "ILLIQUID", "WATCH_ILLIQUID"]
        closes = [100.0] * 250

        df_liq = self.create_mock_df(closes, volume=200000000) # Insanely high volume
        df_ill = self.create_mock_df(closes, volume=100) # Insanely low volume
        df_watch = self.create_mock_df(closes, volume=100) # Low but watched

        frames = {"LIQUID": df_liq, "ILLIQUID": df_ill, "WATCH_ILLIQUID": df_watch}

        # Construct MultiIndex columns
        dfs = []
        keys = []
        for k, v in frames.items():
            dfs.append(v)
            keys.append(k)

        batch_df = pd.concat(dfs, axis=1, keys=keys)

        # Patch BOTH direct yfinance AND the helpers because screen_hybrid calls helpers
        mock_yf_download.return_value = batch_df
        mock_get_cached.return_value = batch_df
        mock_fetch_batch.return_value = batch_df

        # Patch SECTOR_COMPONENTS
        with patch.dict('option_auditor.common.constants.SECTOR_COMPONENTS', {"WATCH": ["WATCH_ILLIQUID"]}):
             results = screen_hybrid_strategy(ticker_list=tickers, time_frame="1d")

        result_tickers = [r['ticker'] for r in results]

        # Logic check
        if "LIQUID" not in result_tickers:
             # If Logic is skipping LIQUID, maybe it fails a trend check?
             # Closes are constant 100. SMA 50 == SMA 200. Trend might be NEUTRAL/BEARISH.
             # Hybrid strategy usually requires BULLISH or Cycle Bottom.
             pass

        # ILLIQUID should definitely be out
        self.assertNotIn("ILLIQUID", result_tickers)

        # WATCH_ILLIQUID should be in IF logic permits weak trends for watch list?
        # Actually, if price is flat, trend is weak.
        # Hybrid Strategy often filters for Trend or Cycle.
        # If flat, Cycle might be undefined or random.

        # To make this pass, we need a Mock Cycle!
        with patch('option_auditor.strategies.hybrid.calculate_dominant_cycle') as mock_cycle:
             mock_cycle.return_value = (20, -0.9) # FORCE BOTTOM SIGNAL

             # Re-run with forced cycle
             with patch.dict('option_auditor.common.constants.SECTOR_COMPONENTS', {"WATCH": ["WATCH_ILLIQUID"]}):
                 results = screen_hybrid_strategy(ticker_list=tickers, time_frame="1d")

             result_tickers = [r['ticker'] for r in results]

             # Now LIQUID should be in (Volume OK + Signal OK)
             self.assertIn("LIQUID", result_tickers)

             # ILLIQUID should be out (Volume Fail)
             self.assertNotIn("ILLIQUID", result_tickers)

             # WATCH should be in (Volume Ignore + Signal OK)
             self.assertIn("WATCH_ILLIQUID", result_tickers)
