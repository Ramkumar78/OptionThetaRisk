import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
# Fix Attribute Error by importing pandas as pd
# option_auditor.sp500_data imports pandas as pd, so we patch pandas.read_html
# directly since it's a top level function that will be called.

class TestSP500Data(unittest.TestCase):
    @patch('pandas.read_html')
    def test_get_sp500_tickers_success(self, mock_read_html):
        from option_auditor.sp500_data import get_sp500_tickers

        # Mock successful HTML table read
        mock_df = pd.DataFrame({'Symbol': ['AAPL', 'BRK.B', 'MMM']})
        mock_read_html.return_value = [mock_df]

        tickers = get_sp500_tickers()

        self.assertIn('AAPL', tickers)
        self.assertIn('BRK-B', tickers) # Verify replacement
        self.assertIn('MMM', tickers)
        self.assertEqual(len(tickers), 3)

    @patch('pandas.read_html')
    def test_get_sp500_tickers_fallback(self, mock_read_html):
        from option_auditor.sp500_data import get_sp500_tickers

        # Mock failure
        mock_read_html.side_effect = Exception("Connection Error")

        tickers = get_sp500_tickers()

        # Verify fallback list
        self.assertTrue(len(tickers) > 0)
        self.assertIn('AAPL', tickers)
        self.assertIn('MSFT', tickers)
        self.assertIn('NVDA', tickers)
