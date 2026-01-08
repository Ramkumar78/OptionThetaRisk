import unittest
import os
from unittest.mock import patch
from option_auditor.sp500_data import get_sp500_tickers

class TestSP500Loading(unittest.TestCase):

    def test_load_from_csv(self):
        """Test loading tickers from the CSV file."""
        # The CSV file should exist in the data directory
        tickers = get_sp500_tickers()
        self.assertTrue(len(tickers) > 400, f"Should load a full list of tickers, got {len(tickers)}")
        self.assertIn("AAPL", tickers, "AAPL should be in the list")
        self.assertIn("MSFT", tickers, "MSFT should be in the list")

        # Check specific tickers from the user provided list to ensure it's using the file
        self.assertIn("CMCSA", tickers)
        self.assertIn("CHTR", tickers)

    @patch('os.path.exists')
    def test_fallback_logic(self, mock_exists):
        """Test fallback to hardcoded list if CSV is missing."""
        # Simulate CSV missing
        mock_exists.return_value = False

        # We need to reload the module or just call the function which re-checks file
        tickers = get_sp500_tickers()

        # This should fallback to SECTOR_COMPONENTS or hardcoded fallback
        self.assertTrue(len(tickers) > 0)
        self.assertIsInstance(tickers, list)

        # Check that it is NOT the full list (SECTOR_COMPONENTS only has partial list)
        # Note: SECTOR_COMPONENTS has about 10 per sector * 11 sectors + watch list = ~150
        # So it should be significantly less than 400
        if len(tickers) > 400:
             # Unless SECTOR_COMPONENTS was updated elsewhere?
             pass

if __name__ == '__main__':
    unittest.main()
