import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime
from option_auditor.master_screener import MasterScreener

class TestMasterScreenerV2(unittest.TestCase):
    def setUp(self):
        self.tickers_us = ["AAPL"]
        self.tickers_uk = []
        self.tickers_india = []
        self.screener = MasterScreener(self.tickers_us, self.tickers_uk, self.tickers_india)

    @patch("option_auditor.master_screener.yf.download")
    def test_fetch_market_regime(self, mock_download):
        dates = pd.date_range(end=datetime.now(), periods=250)
        spy_close = np.linspace(400, 500, 250)
        vix_close = np.full(250, 15.0)

        df = pd.DataFrame({
            ("Close", "SPY"): spy_close,
            ("Close", "^VIX"): vix_close
        }, index=dates)
        df.columns = pd.MultiIndex.from_tuples(df.columns)

        mock_download.return_value = df

        self.screener._fetch_market_regime()

        self.assertEqual(self.screener.market_regime, "BULLISH_AGGRESSIVE")

    @patch("option_auditor.master_screener.yf.download")
    def test_process_stock_vcp_explosion(self, mock_download):
        dates = pd.date_range(end=datetime.now(), periods=300)
        # SPY: Flat performance
        spy_close = np.full(300, 400.0)

        # Stock: Significant Outperformance
        stock_close = np.linspace(100, 200, 300) # +100% vs 0%

        # VCP Logic needs close std dev reduction.
        stock_close[-10:] = 200.0

        volumes = np.full(300, 1000000)
        volumes[-1] = 2000000

        df_stock = pd.DataFrame({
            'Open': stock_close,
            'High': stock_close + 1,
            'Low': stock_close - 1,
            'Close': stock_close,
            'Volume': volumes
        }, index=dates)

        df_market = pd.DataFrame({
            ("Close", "SPY"): spy_close,
            ("Close", "^VIX"): np.full(300, 15.0)
        }, index=dates)
        df_market.columns = pd.MultiIndex.from_tuples(df_market.columns)

        def side_effect(tickers, **kwargs):
            if "SPY" in str(tickers):
                return df_market
            return df_stock

        mock_download.side_effect = side_effect

        results = self.screener.run()
        self.assertTrue(len(results) > 0)
        res = results[0]
        self.assertEqual(res['Ticker'], "AAPL")
        self.assertEqual(res['Setup'], "💥 VCP EXPLOSION")

    @patch("option_auditor.master_screener.yf.download")
    def test_process_stock_fortress_spread(self, mock_download):
        dates = pd.date_range(end=datetime.now(), periods=300)
        spy_close = np.linspace(400, 450, 300)

        stock_close = np.linspace(100, 150, 300)
        highs = stock_close + 5
        lows = stock_close - 5

        stock_close[-10:] = np.linspace(140, 150, 10)

        stock_close[-3:] = [148, 147, 146]
        highs[-3:] = [150, 149, 148]
        lows[-3:] = [145, 144, 143]

        df_stock = pd.DataFrame({
            'Open': stock_close,
            'High': highs,
            'Low': lows,
            'Close': stock_close,
            'Volume': np.full(300, 1000000)
        }, index=dates)

        df_market = pd.DataFrame({
            ("Close", "SPY"): spy_close,
            ("Close", "^VIX"): np.full(300, 15.0)
        }, index=dates)
        df_market.columns = pd.MultiIndex.from_tuples(df_market.columns)

        def side_effect(tickers, **kwargs):
            if "SPY" in str(tickers):
                return df_market
            return df_stock

        mock_download.side_effect = side_effect

        results = self.screener.run()

        if len(results) > 0:
             res = results[0]
             self.assertIn("FORTRESS", res['Setup'])

if __name__ == '__main__':
    unittest.main()
