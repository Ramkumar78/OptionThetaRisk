import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date, timedelta
from option_auditor.screener import screen_bull_put_spreads

class TestBullPutScreener(unittest.TestCase):
    def test_bull_put_spreads_logic(self):
        """
        Tests that the Bull Put Spread screener correctly:
        1. Uses Ticker.history (not yf.download)
        2. Filters by SMA trend
        3. Selects correct strikes based on delta
        4. Calculates ROI and Price correctly
        """
        # Patch yfinance globally since it is imported inside the function
        with patch('yfinance.Ticker') as mock_Ticker, \
             patch('option_auditor.screener._calculate_put_delta') as mock_delta:

            # Setup Ticker Factory to return different data for different tickers
            def side_effect_Ticker(ticker):
                instance = MagicMock()

                # 1. Setup History Data
                # Create data such that:
                # NVDA: Price 180 > SMA 50 (Say SMA is 170) -> BULLISH
                # AMD: Price 120 > SMA 50 (Say SMA is 110) -> BULLISH
                # BAD: Price 50 < SMA 50 (Say SMA is 60) -> BEARISH (Should be filtered)

                price = 100.0
                if ticker == "NVDA": price = 180.0
                elif ticker == "AMD": price = 120.0
                elif ticker == "BAD": price = 50.0

                dates = pd.date_range(end=pd.Timestamp.now(), periods=60)
                # Create a trend.
                # For BULLISH, Price > Rolling Mean.
                # Flat price works if we cheat the SMA calc or provide long history where past was lower.
                # Let's just provide constant price and ensure SMA calculation works.
                # If constant, Price == SMA. Code checks: if curr_price < sma_50: return None.
                # 180 < 180 is False. It passes.
                # For BAD, we make price drop at the end.

                prices = [price] * 60
                if ticker == "BAD":
                    # SMA will be higher if past prices were higher
                    prices = [60.0] * 50 + [50.0] * 10
                    # SMA approx 58. Current 50. 50 < 58. Filtered.

                df = pd.DataFrame({
                    "Open": prices,
                    "High": prices,
                    "Low": prices,
                    "Close": prices,
                    "Volume": [1000000] * 60
                }, index=dates)

                instance.history.return_value = df

                # 2. Setup Options
                today = date.today()
                valid_expiry = today + timedelta(days=45)
                valid_expiry_str = valid_expiry.strftime("%Y-%m-%d")
                instance.options = [valid_expiry_str]

                # 3. Setup Option Chain
                def side_effect_chain(date):
                    # Create strikes
                    strikes = np.arange(50, 300, 5)
                    # Prices needed for Credit calculation
                    # Credit = Short Bid - Long Ask
                    # We need Positive Credit.
                    # Puts: Higher Strike = Higher Price.
                    # Short (Higher K) - Long (Lower K) > 0.

                    # Let's define price curve
                    put_prices = strikes * 0.1

                    puts = pd.DataFrame({
                        "strike": strikes,
                        "bid": put_prices - 0.05,
                        "ask": put_prices + 0.05,
                        "impliedVolatility": [0.4] * len(strikes),
                        "lastPrice": put_prices
                    })
                    return MagicMock(puts=puts)

                instance.option_chain.side_effect = side_effect_chain

                return instance

            mock_Ticker.side_effect = side_effect_Ticker

            # Setup Delta Mock
            # We want to select specific strikes.
            # NVDA (180): Short ~170 (Delta -0.30). Long 165.
            # AMD (120): Short ~110 (Delta -0.30). Long 105.
            def side_effect_delta(S, K, T, r, sigma):
                # Return -0.30 if K is "close" to target
                target = S - 10
                if abs(K - target) < 2.5:
                    return -0.30
                return -0.10

            mock_delta.side_effect = side_effect_delta

            # Execute
            results = screen_bull_put_spreads(["NVDA", "AMD", "BAD"], min_roi=0.01)

            # Assertions
            self.assertEqual(len(results), 2, "Should return 2 results (NVDA, AMD), BAD should be filtered")

            nvda = next((r for r in results if r['ticker'] == "NVDA"), None)
            amd = next((r for r in results if r['ticker'] == "AMD"), None)

            self.assertIsNotNone(nvda)
            self.assertIsNotNone(amd)

            # Check Prices
            self.assertEqual(nvda['price'], 180.0)
            self.assertEqual(amd['price'], 120.0)

            # Check Strategy Details
            # NVDA Short Strike should be 170 (180-10)
            self.assertEqual(nvda['short_strike'], 170.0)
            # Long Strike should be 165
            self.assertEqual(nvda['long_strike'], 165.0)

            # Check Credit
            # Short Bid (170): 17.0 - 0.05 = 16.95
            # Long Ask (165): 16.5 + 0.05 = 16.55
            # Credit = 16.95 - 16.55 = 0.40
            self.assertAlmostEqual(nvda['credit'], 0.40)

if __name__ == '__main__':
    unittest.main()
