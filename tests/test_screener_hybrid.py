import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_hybrid_strategy

class TestScreenerHybrid(unittest.TestCase):

    @patch('option_auditor.screener.yf.download')
    @patch('option_auditor.screener.SECTOR_COMPONENTS', {"WATCH": ["AAPL"]})
    def test_screen_hybrid_strategy_bullish_bottom(self, mock_download):
        """Test Scenario A: Bullish Trend + Cycle Bottom"""
        # Create dummy data for 2 years (approx 500 days)
        dates = pd.date_range(end='2023-01-01', periods=500)

        df = pd.DataFrame({
            'Close': np.linspace(100, 200, 500), # Uptrend
            'High': np.linspace(105, 205, 500),
            'Low': np.linspace(95, 195, 500),
            'Open': np.linspace(100, 200, 500),
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        # Mock download return
        mock_download.return_value = df

        with patch('option_auditor.screener._calculate_dominant_cycle') as mock_cycle:
            # Scenario A: Bullish (Price > SMA200) + Bottom (Rel pos <= -0.7)
            # Our data is strictly uptrend, so Price (200) > SMA200 (approx 150).
            # Force Cycle Bottom
            mock_cycle.return_value = (20.0, -0.9) # Period 20, Rel Pos -0.9

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['ticker'], "TEST")
            self.assertEqual(r['trend'], "BULLISH")
            self.assertIn("BOTTOM", r['cycle'])
            self.assertIn("PERFECT BUY", r['verdict'])
            self.assertEqual(r['score'], 95)

            # Verify new fields
            self.assertIn('stop_loss', r)
            self.assertIn('target', r)
            self.assertIn('rr_ratio', r)

            # Check values roughly
            # ATR approx (High-Low) = 10 (constant in my simple mock)
            # Actually pandas_ta atr uses True Range.
            # Here High-Low = 10. Close-PrevClose ~ 0.2.
            # So ATR should be close to 10.
            # Stop = Close - 3*ATR = 200 - 30 = 170
            # Target = Close + 2*ATR = 200 + 20 = 220

            self.assertTrue(160 < r['stop_loss'] < 180, f"Stop loss {r['stop_loss']} not near expected 170")
            self.assertTrue(210 < r['target'] < 230, f"Target {r['target']} not near expected 220")


    @patch('option_auditor.screener.yf.download')
    def test_screen_hybrid_strategy_bearish_top(self, mock_download):
        """Test Scenario C: Bearish Trend + Cycle Top"""
        dates = pd.date_range(end='2023-01-01', periods=500)

        # Bearish: Downtrend
        df = pd.DataFrame({
            'Close': np.linspace(200, 100, 500),
            'High': np.linspace(205, 105, 500),
            'Low': np.linspace(195, 95, 500),
            'Open': np.linspace(200, 100, 500),
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        mock_download.return_value = df

        with patch('option_auditor.screener._calculate_dominant_cycle') as mock_cycle:
            # Bearish (Price 100 < SMA200 150) + Top (Rel Pos >= 0.7)
            mock_cycle.return_value = (20.0, 0.8)

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['trend'], "BEARISH")
            self.assertIn("TOP", r['cycle'])
            self.assertIn("PERFECT SHORT", r['verdict'])
            self.assertEqual(r['color'], "red")

    @patch('option_auditor.screener.yf.download')
    def test_screen_hybrid_strategy_momentum_buy(self, mock_download):
        """Test Scenario B: Bullish + Breakout (High > 50d High)"""
        dates = pd.date_range(end='2023-01-01', periods=500)

        # Bullish
        closes = np.linspace(100, 200, 500)
        # Make a breakout at the end
        closes[-1] = 210 # Spike

        highs = np.linspace(105, 205, 500)
        # 50d high check: shift(1). Max of last 50 before today.
        # If we set today's close > max(prev 50 highs).
        # Previous max high is around 205. Today close 210. Breakout!

        df = pd.DataFrame({
            'Close': closes,
            'High': highs,
            'Low': np.linspace(95, 195, 500),
            'Open': np.linspace(100, 200, 500),
            'Volume': np.random.randint(1000000, 2000000, 500)
        }, index=dates)

        mock_download.return_value = df

        with patch('option_auditor.screener._calculate_dominant_cycle') as mock_cycle:
            # Cycle MID (Neutral)
            mock_cycle.return_value = (20.0, 0.0)

            results = screen_hybrid_strategy(ticker_list=["TEST"])

            self.assertEqual(len(results), 1)
            r = results[0]
            self.assertEqual(r['trend'], "BULLISH")
            # Should match BREAKOUT BUY
            self.assertIn("BREAKOUT BUY", r['verdict'])
            self.assertEqual(r['score'], 85)
