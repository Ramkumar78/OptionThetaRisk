import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.master_screener import MasterScreener
from option_auditor.uk_stock_data import get_uk_tickers

class TestMasterScreenerV2(unittest.TestCase):

    def setUp(self):
        self.us_tickers = ["AAPL", "MSFT"]
        self.uk_tickers = ["AZN.L", "BP.L"]
        self.screener = MasterScreener(self.us_tickers, self.uk_tickers)

    def test_fresh_breakout_logic(self):
        # Scenario: Price below 20-day high for a while, then breaks out today
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        df = pd.DataFrame(index=dates)
        df['Close'] = 100.0
        df['High'] = 102.0 # Consistent high
        df['Low'] = 98.0
        df['Volume'] = 5000000

        # Breakout today
        df.iloc[-1, df.columns.get_loc('Close')] = 105.0

        res_date, days_ago = self.screener._find_fresh_breakout(df)
        self.assertIsNotNone(res_date)
        self.assertEqual(days_ago, 0) # Today

    def test_stale_breakout_logic(self):
        # Scenario: Price broke out 10 days ago and stayed up.
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        df = pd.DataFrame(index=dates)
        df['Close'] = 100.0
        df['High'] = 100.0
        df['Low'] = 90.0
        df['Volume'] = 5000000

        # Breakout happened 10 days ago
        df.iloc[-10:, df.columns.get_loc('Close')] = 110.0
        df.iloc[-10:, df.columns.get_loc('High')] = 112.0

        res_date, days_ago = self.screener._find_fresh_breakout(df)
        self.assertIsNone(res_date)

    def test_process_stock_priority_logic(self):
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)

        # Prices construction to ensure distinct SMAs
        # The key is to have SMA 50 > SMA 150 > SMA 200
        # And Current Price > SMA 50

        # Let's use simple increasing function but flat enough to make SMAs lag
        # e.g. Linear
        # p(t) = t
        # SMA_N(t) = t - (N-1)/2
        # So SMA_50 = t - 24.5
        # SMA_150 = t - 74.5
        # SMA_200 = t - 99.5
        # Price = t

        # t > t - 24.5 (True)
        # t - 24.5 > t - 74.5 (True)
        # t - 74.5 > t - 99.5 (True)

        # So simple linear increasing price ensures trend alignment.

        prices = np.linspace(100, 200, 300)

        df = pd.DataFrame({'Close': prices, 'High': prices*1.01, 'Low': prices*0.99, 'Volume': [5000000]*300}, index=dates)

        # Mock `_find_fresh_breakout` to return success (Trigger ISA)
        self.screener._find_fresh_breakout = MagicMock(return_value=("2023-01-01", 0))

        with patch('pandas_ta.rsi') as mock_rsi, \
             patch('pandas_ta.atr') as mock_atr:

            # RSI < 45 to trigger option signal (if no ISA)
            # If RSI is < 45 on an uptrend, it's a pullback.
            mock_rsi.return_value = pd.Series([30]*300, index=dates)

            # ATR % > 2.5
            # Price 200. ATR > 5. Let's make ATR 10.
            mock_atr.return_value = pd.Series([10]*300, index=dates)

            res = self.screener._process_stock("AAPL", df)

            self.assertIsNotNone(res)
            # Should be ISA BUY because it has priority
            self.assertIn("ISA BUY", res['Type'])
            self.assertNotIn("OPT SELL", res['Type'])

    def test_uk_list(self):
        tickers = get_uk_tickers()
        self.assertTrue(len(tickers) > 100)
        self.assertIn("AZN.L", tickers)

if __name__ == '__main__':
    unittest.main()
