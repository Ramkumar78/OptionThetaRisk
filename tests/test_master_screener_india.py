import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.master_screener import screen_master_convergence, FortressScreener

class TestMasterScreenerIndia(unittest.TestCase):
    def setUp(self):
        # Create a dummy DataFrame for mocking yfinance data
        dates = pd.date_range(start="2023-01-01", periods=300)
        data = {
            "Open": np.linspace(100, 200, 300),
            "High": np.linspace(105, 205, 300),
            "Low": np.linspace(95, 195, 300),
            "Close": np.linspace(100, 200, 300),
            "Volume": np.random.randint(1000000, 5000000, 300)
        }
        self.mock_df = pd.DataFrame(data, index=dates)

        # Mock SPY and VIX for regime
        self.spy_df = pd.DataFrame({"Close": np.linspace(400, 450, 300)}, index=dates)
        self.vix_df = pd.DataFrame({"Close": np.random.uniform(10, 25, 300)}, index=dates)

    @patch("option_auditor.master_screener.yf.download")
    def test_india_region_tickers(self, mock_download):
        # Setup mock to return different data based on tickers
        def side_effect(tickers, **kwargs):
            if "SPY" in tickers:
                # Return SPY/VIX data
                mi = pd.MultiIndex.from_product([["Close"], ["SPY", "^VIX"]])
                df = pd.DataFrame(index=self.mock_df.index, columns=mi)
                df[("Close", "SPY")] = self.spy_df["Close"]
                df[("Close", "^VIX")] = self.vix_df["Close"]
                return df

            else:
                # Return stock data
                if isinstance(tickers, list) and len(tickers) > 1:
                     frames = {}
                     for t in tickers:
                         frames[t] = self.mock_df
                     return pd.concat(frames, axis=1)
                elif isinstance(tickers, list) and len(tickers) == 1:
                     return self.mock_df
                else:
                     return self.mock_df

        mock_download.side_effect = side_effect

        results = screen_master_convergence(region="india")

        # Check internal behavior by ensuring we got a list back
        self.assertTrue(isinstance(results, list))

    @patch("option_auditor.master_screener.FortressScreener")
    def test_initialization_tickers(self, MockScreener):
        # Test that the correct tickers are passed to FortressScreener based on region

        MockScreener.return_value.run_screen.return_value = []

        # Test India
        screen_master_convergence(region="india")

        # Capture args/kwargs from the constructor call
        # MockScreener is the class, so calling it (instantiation) is the call we want to check
        # call_args returns (args, kwargs) of the last call

        call_args = MockScreener.call_args
        self.assertIsNotNone(call_args, "FortressScreener was not called")

        args, kwargs = call_args

        # The constructor signature is: def __init__(self, tickers_us=None, tickers_uk=None, tickers_india=None):
        # The code calls: FortressScreener(tickers_us=us, tickers_uk=uk, tickers_india=india)

        tickers_us = kwargs.get('tickers_us', args[0] if len(args) > 0 else None)
        tickers_uk = kwargs.get('tickers_uk', args[1] if len(args) > 1 else None)
        tickers_india = kwargs.get('tickers_india', args[2] if len(args) > 2 else None)

        self.assertEqual(tickers_us, [])
        self.assertEqual(tickers_uk, [])
        self.assertIsNotNone(tickers_india)
        self.assertTrue(len(tickers_india) > 0)
        # Check for a known India ticker in the list (from fallback or file)
        self.assertTrue(any("RELIANCE.NS" in t for t in tickers_india))

        # Test US (Default)
        screen_master_convergence(region="us")
        args, kwargs = MockScreener.call_args
        tickers_us = kwargs.get('tickers_us', args[0] if len(args) > 0 else None)
        tickers_india = kwargs.get('tickers_india', args[2] if len(args) > 2 else None)

        self.assertTrue(len(tickers_us) > 0)
        self.assertEqual(tickers_india, [])

        # Test UK
        screen_master_convergence(region="uk")
        args, kwargs = MockScreener.call_args
        tickers_uk = kwargs.get('tickers_uk', args[1] if len(args) > 1 else None)
        tickers_india = kwargs.get('tickers_india', args[2] if len(args) > 2 else None)

        self.assertTrue(len(tickers_uk) > 0)
        self.assertEqual(tickers_india, [])

if __name__ == "__main__":
    unittest.main()
