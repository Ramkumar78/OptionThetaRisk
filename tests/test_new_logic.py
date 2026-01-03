import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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
        ticker = "RELIANCE.NS"

        # Setup Dates
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=300)

        # Construct Valid Trend Data
        # Price > 50 > 150 > 200
        closes = np.zeros(300)
        closes[0:100] = 2000
        closes[100:200] = 2200
        closes[200:280] = 2400
        closes[280:] = 2500

        # Create Breakout
        # Previous 20 days (260-280) high was 2400.
        # Now we are at 2500.
        # But wait, logic: _find_fresh_breakout
        # Pivot = rolling(20).max().shift(1)
        # Recent = last 10 days.
        # if recent > pivot -> breakout.
        # Ensure pivot is established below current price.

        df = pd.DataFrame({
            'Open': closes,
            'High': closes + 10,
            'Low': closes - 10,
            'Close': closes,
            'Volume': np.full(300, 1000000) # Liquid
        }, index=dates)

        # Make a clear breakout at the end
        # Last 20 days: Price was 2400.
        # Last 3 days: Price jumps to 2500.
        df.iloc[-20:-3, df.columns.get_loc('Close')] = 2400
        df.iloc[-20:-3, df.columns.get_loc('High')] = 2405

        df.iloc[-3:, df.columns.get_loc('Close')] = 2500
        df.iloc[-3:, df.columns.get_loc('High')] = 2510

        # Mock Market Data (SPY, VIX)
        market_df = pd.DataFrame({
            ("Close", "SPY"): np.linspace(400, 500, 300),
            ("Close", "^VIX"): np.full(300, 15.0),
        }, index=dates)
        market_df.columns = pd.MultiIndex.from_tuples(market_df.columns)

        def side_effect(tickers, **kwargs):
            if "SPY" in str(tickers):
                return market_df

            # Ticker Data: Return FLAT DataFrame for single ticker
            return df

        mock_download.side_effect = side_effect

        screener = MasterScreener([], [], [ticker])
        results = screener.run()

        self.assertTrue(len(results) > 0, "Should return results for valid setup")
        res = results[0]
        self.assertEqual(res['Ticker'], ticker)
        self.assertIn("BUY", res['Type'])

    @patch("option_auditor.master_screener.yf.download")
    def test_master_screener_us_isa_logic(self, mock_download):
        """Test US specific logic: ISA BUY label."""
        ticker = "AAPL"

        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=300)

        # Construct Valid Trend Data
        closes = np.zeros(300)
        closes[0:100] = 150
        closes[100:200] = 170
        closes[200:280] = 190
        closes[280:] = 200

        df = pd.DataFrame({
            'Open': closes,
            'High': closes + 5,
            'Low': closes - 5,
            'Close': closes,
            'Volume': np.full(300, 10000000)
        }, index=dates)

        # Breakout
        df.iloc[-20:-3, df.columns.get_loc('Close')] = 190
        df.iloc[-20:-3, df.columns.get_loc('High')] = 195

        df.iloc[-3:, df.columns.get_loc('Close')] = 205
        df.iloc[-3:, df.columns.get_loc('High')] = 210

        market_df = pd.DataFrame({
            ("Close", "SPY"): np.linspace(400, 500, 300),
            ("Close", "^VIX"): np.full(300, 15.0),
        }, index=dates)
        market_df.columns = pd.MultiIndex.from_tuples(market_df.columns)

        def side_effect(tickers, **kwargs):
            if "SPY" in str(tickers):
                return market_df

            # Ticker Data: Return FLAT DataFrame for single ticker
            return df

        mock_download.side_effect = side_effect

        screener = MasterScreener([ticker], [], [])
        results = screener.run()

        self.assertTrue(len(results) > 0, "Should return results for valid setup")
        self.assertEqual(results[0]['Type'], "🇺🇸 ISA BUY")

class TestAppRoute(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    @patch("webapp.app.MasterScreener")
    def test_screen_master_route_india(self, MockScreener):
        """Test that /screen/master with region=india instantiates MasterScreener with India tickers."""
        instance = MockScreener.return_value
        instance.run.return_value = [{"Ticker": "RELIANCE.NS", "Price": 2500}]

        with patch("option_auditor.india_stock_data.INDIAN_TICKERS_RAW", ["RELIANCE.NS"]):
            response = self.client.get("/screen/master?region=india")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['Ticker'], "RELIANCE.NS")

            args, _ = MockScreener.call_args
            self.assertEqual(args[2], ["RELIANCE.NS"])

if __name__ == '__main__':
    unittest.main()
