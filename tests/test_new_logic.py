import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.sp500_data import get_sp500_tickers
from option_auditor.master_screener import MasterScreener
from webapp.app import create_app
import json

class TestSP500Data(unittest.TestCase):
    def test_get_sp500_tickers(self):
        """Verify that get_sp500_tickers aggregates SECTOR_COMPONENTS correctly."""
        # We can patch SECTOR_COMPONENTS to ensure we are testing the logic
        with patch("option_auditor.sp500_data.SECTOR_COMPONENTS", {
            "Tech": ["AAPL", "MSFT"],
            "Finance": ["JPM"],
            "WATCH": ["SHOULD_BE_EXCLUDED"]
        }):
            tickers = get_sp500_tickers()
            self.assertIn("AAPL", tickers)
            self.assertIn("MSFT", tickers)
            self.assertIn("JPM", tickers)
            self.assertNotIn("SHOULD_BE_EXCLUDED", tickers)
            self.assertEqual(len(tickers), 3)

    def test_get_sp500_tickers_fallback(self):
        """Verify fallback mechanism if SECTOR_COMPONENTS raises exception (simulated)."""
        with patch("option_auditor.sp500_data.SECTOR_COMPONENTS", side_effect=Exception("Boom")):
            # Note: accessing SECTOR_COMPONENTS won't raise, iterating it might if it's not dict-like
            # But here we mocked the import name.
            # To simulate exception inside function, let's mock the .items method
             mock_sectors = MagicMock()
             mock_sectors.items.side_effect = Exception("Boom")
             with patch("option_auditor.sp500_data.SECTOR_COMPONENTS", mock_sectors):
                 tickers = get_sp500_tickers()
                 self.assertIn("SPY", tickers)

class TestMasterScreener(unittest.TestCase):
    @patch("option_auditor.master_screener.yf.download")
    def test_master_screener_india_logic(self, mock_download):
        """Test India specific logic: Non-ISA label, Liquidity check."""

        # Setup specific ticker mock
        ticker = "RELIANCE.NS"

        # Create a DataFrame that passes liquidity and trend checks
        # Price: 2500 INR
        # Volume: 1,000,000 (Turnover = 2.5B INR > 100M INR limit)
        # Trend: > 50 SMA, 50 > 150 > 200.
        # Breakout: recent high check.

        dates = pd.date_range(start="2023-01-01", periods=300)
        data = {
            "Close": np.linspace(2000, 2500, 300),
            "High": np.linspace(2010, 2510, 300),
            "Low": np.linspace(1990, 2490, 300),
            "Volume": np.full(300, 1000000)
        }
        df = pd.DataFrame(data, index=dates)

        # Mocking breakout: Needs a pivot.
        # Let's make the last few days spike to ensure breakout
        df.iloc[-1, df.columns.get_loc("Close")] = 2600
        df.iloc[-1, df.columns.get_loc("High")] = 2650

        # Mock download return
        # yfinance download(group_by='ticker') returns MultiIndex if multiple, or single if one.
        # MasterScreener handles chunking.

        # We need to mock market regime fetch first, then stock fetch.
        # MasterScreener calls _fetch_market_regime first.

        # Mock Market Data (SPY, VIX)
        market_df = pd.DataFrame({
            ("SPY", "Close"): np.linspace(400, 500, 300),
            ("SPY", "High"): np.linspace(400, 500, 300),
            ("SPY", "Low"): np.linspace(400, 500, 300),
            ("SPY", "Volume"): np.full(300, 1000000),
            ("^VIX", "Close"): np.full(300, 15.0),
            ("^VIX", "High"): np.full(300, 16.0),
            ("^VIX", "Low"): np.full(300, 14.0),
            ("^VIX", "Volume"): np.full(300, 1000000)
        }, index=dates)
        market_df.columns = pd.MultiIndex.from_tuples(market_df.columns)

        # Mock Ticker Data
        ticker_df = df.copy()
        # To make yf.download return consistent structure for single ticker in chunk
        # If we pass one ticker, it might return simple DF.
        # MasterScreener handles both.

        def side_effect(tickers, **kwargs):
            if "SPY" in tickers:
                return market_df
            if ticker in tickers:
                # Chunk download
                # Return dict-like or simple DF depending on implementation expectations
                # Implementation expects: data[ticker] or data if simple.
                # If we return a dataframe with columns (Ticker, Field) it works best for group_by
                m_cols = pd.MultiIndex.from_product([[ticker], ["Close", "High", "Low", "Volume"]])
                d = pd.DataFrame(index=dates, columns=m_cols)
                d[(ticker, "Close")] = ticker_df["Close"]
                d[(ticker, "High")] = ticker_df["High"]
                d[(ticker, "Low")] = ticker_df["Low"]
                d[(ticker, "Volume")] = ticker_df["Volume"]
                return d
            return pd.DataFrame()

        mock_download.side_effect = side_effect

        screener = MasterScreener([], [], [ticker])
        results = screener.run()

        self.assertTrue(len(results) > 0)
        res = results[0]
        self.assertEqual(res['Ticker'], ticker)
        self.assertEqual(res['Type'], "🇮🇳 BUY (Non-ISA)")
        # Check if liquidity check passed (it should have)

    @patch("option_auditor.master_screener.yf.download")
    def test_master_screener_us_isa_logic(self, mock_download):
        """Test US specific logic: ISA BUY label."""
        ticker = "AAPL"
        dates = pd.date_range(start="2023-01-01", periods=300)

        # Similar uptrend data
        data = {
            "Close": np.linspace(150, 200, 300),
            "High": np.linspace(155, 205, 300),
            "Low": np.linspace(145, 195, 300),
            "Volume": np.full(300, 5000000) # Liquid
        }
        df = pd.DataFrame(data, index=dates)
        df.iloc[-1, df.columns.get_loc("Close")] = 210 # Breakout
        df.iloc[-1, df.columns.get_loc("High")] = 215

        # Mock Market Data (SPY, VIX) - Bullish
        market_df = pd.DataFrame({
            ("SPY", "Close"): np.linspace(400, 500, 300),
            ("^VIX", "Close"): np.full(300, 15.0),
        }, index=dates)
        market_df.columns = pd.MultiIndex.from_tuples(market_df.columns)

        def side_effect(tickers, **kwargs):
            if "SPY" in tickers:
                return market_df
            if ticker in tickers:
                m_cols = pd.MultiIndex.from_product([[ticker], ["Close", "High", "Low", "Volume"]])
                d = pd.DataFrame(index=dates, columns=m_cols)
                d[(ticker, "Close")] = df["Close"]
                d[(ticker, "High")] = df["High"]
                d[(ticker, "Low")] = df["Low"]
                d[(ticker, "Volume")] = df["Volume"]
                return d
            return pd.DataFrame()

        mock_download.side_effect = side_effect

        screener = MasterScreener([ticker], [], [])
        results = screener.run()

        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['Type'], "🇺🇸 ISA BUY")

class TestAppRoute(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    @patch("webapp.app.MasterScreener")
    def test_screen_master_route_india(self, MockScreener):
        """Test that /screen/master with region=india instantiates MasterScreener with India tickers."""
        # Setup mock instance
        instance = MockScreener.return_value
        instance.run.return_value = [{"Ticker": "RELIANCE.NS", "Price": 2500}]

        # Patch INDIAN_TICKERS_RAW
        with patch("webapp.app.INDIAN_TICKERS_RAW", ["RELIANCE.NS"]):
            response = self.client.get("/screen/master?region=india")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['Ticker'], "RELIANCE.NS")

            # Verify MasterScreener was called with India tickers
            # args: (us, uk, india)
            args, _ = MockScreener.call_args
            self.assertEqual(args[2], ["RELIANCE.NS"])

if __name__ == '__main__':
    unittest.main()
