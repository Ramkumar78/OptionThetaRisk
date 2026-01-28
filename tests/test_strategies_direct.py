import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date, timedelta

from option_auditor.strategies.bull_put import screen_bull_put_spreads
from option_auditor.strategies.squeeze import screen_bollinger_squeeze

class TestStrategiesDirect(unittest.TestCase):

    # --- Bull Put Tests ---
    @patch('option_auditor.strategies.bull_put.resolve_region_tickers')
    @patch('yfinance.Ticker')
    def test_bull_put_direct(self, mock_ticker, mock_resolve):
        # 1. Setup Mock Tickers
        mock_resolve.return_value = ["TEST_TICKER"]

        tk = MagicMock()
        mock_ticker.return_value = tk

        # Mock History (Bullish Trend > SMA 50)
        # Price 100, SMA(50) < 100.
        # Need > 200 periods
        prices = [90.0] * 150 + [100.0] * 60
        dates = pd.date_range(end=pd.Timestamp.now(), periods=210)
        df = pd.DataFrame({
            'Close': prices,
            'Volume': [2000000] * 210,
            'High': [105]*210, 'Low': [85]*210, 'Open': [90]*210
        }, index=dates)
        tk.history.return_value = df

        # Mock Options
        tk.options = [(date.today() + timedelta(days=45)).strftime("%Y-%m-%d")]

        # Mock Chain
        # Short Strike: Delta -0.30. Price 100.
        # Implies OTM Put. Strike < 100.
        # Say Strike 90 is Delta -0.30.
        # Long Strike: 85 (width 5).

        # We need _calculate_put_delta to calculate delta.
        # But we are testing the orchestrator.
        # The code calculates delta using Black-Scholes.
        # We can't easily mock the delta calc without patching the internal import in the module.
        # Let's patch `option_auditor.strategies.bull_put._calculate_put_delta`.

        with patch('option_auditor.strategies.bull_put._calculate_put_delta') as mock_calc_delta:
            def delta_side_effect(S, K, T, r, sigma):
                if K == 90: return -0.30
                if K == 85: return -0.10
                return -0.50
            mock_calc_delta.side_effect = delta_side_effect

            # Setup Chain DataFrame
            # Strikes: 80, 85, 90, 95
            chain_df = pd.DataFrame({
                'strike': [80.0, 85.0, 90.0, 95.0],
                'bid': [0.1, 0.2, 0.5, 1.0], # Short 90 bid=0.5. Long 85 ask=0.3?
                'ask': [0.2, 0.3, 0.6, 1.1],
                'impliedVolatility': [0.2] * 4,
                'lastPrice': [0.15, 0.25, 0.55, 1.05]
            })
            tk.option_chain.return_value.puts = chain_df

            # Run
            results = screen_bull_put_spreads(["TEST_TICKER"], min_roi=0.01)

            self.assertEqual(len(results), 1)
            res = results[0]
            self.assertEqual(res['ticker'], "TEST_TICKER")
            self.assertEqual(res['short_strike'], 90.0)
            self.assertEqual(res['long_strike'], 85.0)

            # Credit: Short Bid (0.5) - Long Ask (0.3) = 0.20
            # Function returns credit * 100 = 20.0
            self.assertAlmostEqual(res['credit'], 20.0)

    # --- Squeeze Tests ---
    @patch('option_auditor.strategies.squeeze.ScreeningRunner')
    def test_squeeze_direct(self, MockRunner):
        # 1. Setup Mock Runner
        runner_instance = MockRunner.return_value
        runner_instance.is_intraday = False
        runner_instance.yf_interval = '1d'

        # We need to simulate runner.run(strategy).
        # We can manually invoke the strategy function passed to runner.run.

        def run_side_effect(strategy_func):
            # Create a Mock DF that triggers Squeeze
            # BB inside KC.
            # BB Width < KC Width.
            # BB(20, 2) vs KC(20, 1.5).

            # If price is perfectly constant: StdDev=0 (BB collapsed), ATR=0 (KC collapsed).
            # If price varies slightly:
            # BB = Mean +/- 2*Std. KC = EMA +/- 1.5*ATR.
            # Squeeze ON if BB_Upper < KC_Upper AND BB_Lower > KC_Lower.
            # Basically StdDev needs to be very low relative to ATR.

            dates = pd.date_range(end=pd.Timestamp.now(), periods=100)

            # Low volatility close (std dev low)
            closes = [100.0] * 100
            # High volatility range (high ATR)
            highs = [105.0] * 100
            lows = [95.0] * 100

            df = pd.DataFrame({
                'Open': closes, 'High': highs, 'Low': lows, 'Close': closes, 'Volume': [1000]*100
            }, index=dates)

            return [strategy_func("TEST_SQ", df)]

        runner_instance.run.side_effect = run_side_effect

        results = screen_bollinger_squeeze(["TEST_SQ"])

        self.assertEqual(len(results), 1)
        res = results[0]
        # Since logic returns None on failure, we check for success
        if res:
            self.assertEqual(res['ticker'], "TEST_SQ")
            self.assertEqual(res['squeeze_status'], "ON")
        else:
            self.fail("Strategy returned None for valid squeeze setup")

if __name__ == '__main__':
    unittest.main()
