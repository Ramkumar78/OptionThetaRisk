import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_bollinger_squeeze

class TestScreenerSqueeze(unittest.TestCase):

    @patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
    def test_screen_bollinger_squeeze_logic(self, mock_fetch):
        dates = pd.date_range(end=pd.Timestamp.today(), periods=50)

        # Ticker A: SQUEEZE (Low Volatility)
        # Constant Close -> StdDev=0 -> BB collapsed.
        # High/Low difference -> ATR=2 -> KC Wide.
        df_sq = pd.DataFrame({
            'Open': 100.0, 'High': 101.0, 'Low': 99.0, 'Close': 100.0, 'Volume': 1000000
        }, index=dates)

        # Ticker B: WIDE (Trending)
        # Strong trend expands BB (StdDev of price) much more than ATR.
        vals = [100.0 + i*5.0 for i in range(50)] # 100, 105, 110...
        df_wide = pd.DataFrame({
            'Open': vals,
            'High': [v+1 for v in vals],
            'Low': [v-1 for v in vals],
            'Close': vals,
            'Volume': 1000000
        }, index=dates)

        # Mock Return: MultiIndex Columns
        mock_data = pd.concat([df_sq, df_wide], axis=1, keys=['SQ', 'WIDE'])
        mock_fetch.return_value = mock_data

        # 2. Run Screener
        results = screen_bollinger_squeeze(ticker_list=['SQ', 'WIDE'])

        # 3. Verify
        tickers_found = [r['ticker'] for r in results]

        # Debug info
        if 'SQ' not in tickers_found or 'WIDE' in tickers_found:
            print("Results returned:", results)

        self.assertIn('SQ', tickers_found)
        self.assertNotIn('WIDE', tickers_found)

        res_sq = next(r for r in results if r['ticker'] == 'SQ')
        self.assertEqual(res_sq['squeeze_status'], 'ON')

if __name__ == '__main__':
    unittest.main()
