
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from webapp.app import create_app
from option_auditor.master_screener import MasterScreener

class TestMasterScreener(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    @patch('option_auditor.master_screener.ta')
    @patch('option_auditor.master_screener.yf.download')
    def test_master_screener_logic_green_regime(self, mock_download, mock_ta):
        # Configure ta mocks to pass filters
        mock_atr_series = MagicMock()
        mock_atr_series.iloc = MagicMock()
        mock_atr_series.iloc.__getitem__.return_value = 5.0 # ATR
        mock_ta.atr.return_value = mock_atr_series

        mock_rsi_series = MagicMock()
        mock_rsi_series.iloc = MagicMock()
        mock_rsi_series.iloc.__getitem__.return_value = 60.0 # RSI between 50 and 70
        mock_ta.rsi.return_value = mock_rsi_series

        # 1. Mock Data for Regime Check (Green: SPY > SMA200, VIX < 20)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)

        # SPY: Steady uptrend above 200 SMA
        spy_prices = np.linspace(400, 500, 300)
        vix_prices = np.full(300, 15.0) # VIX low

        # Mocking the first call (Regime Check)
        full_df = pd.DataFrame({
            ('Close', 'SPY'): spy_prices,
            ('Close', '^VIX'): vix_prices,
            ('Open', 'SPY'): spy_prices, # Dummy
        }, index=dates)
        full_df.columns = pd.MultiIndex.from_tuples(full_df.columns)

        # Scan DF
        # Ticker: NVDA. Simulating a buy signal.
        # Price > 200 SMA (we need manual calculation to pass if ta not used for sma, but code uses rolling)
        # Code: sma_200 = df['Close'].rolling(200).mean().iloc[-1]
        # 100 to 150. SMA ~ 125. 150 > 125.

        scan_df = pd.DataFrame({
            ('NVDA', 'Close'): np.linspace(100, 150, 300),
            ('NVDA', 'Open'): np.linspace(100, 150, 300),
            ('NVDA', 'High'): np.linspace(105, 155, 300),
            ('NVDA', 'Low'): np.linspace(95, 145, 300),
            ('NVDA', 'Volume'): np.full(300, 5000000.0)
        }, index=dates)
        scan_df.columns = pd.MultiIndex.from_tuples(scan_df.columns)

        def side_effect(*args, **kwargs):
            tickers = args[0] if args else kwargs.get('tickers')
            if tickers and "SPY" in tickers:
                return full_df
            return scan_df

        mock_download.side_effect = side_effect

        # Instantiate and Run
        screener = MasterScreener(['NVDA'], [])
        results = screener.run()

        # Assertions
        self.assertEqual(screener.regime, "GREEN")
        self.assertTrue(len(results) > 0, "Results should not be empty")
        self.assertEqual(results[0]['Ticker'], 'NVDA')
        self.assertEqual(results[0]['Type'], 'ISA_BUY') # Should be ISA Buy as it's a trend

    @patch('webapp.app.MasterScreener')
    def test_screen_master_route(self, MockMasterScreener):
        # Mock the Council
        mock_instance = MockMasterScreener.return_value
        mock_instance.run.return_value = [
            {
                "Ticker": "NVDA",
                "Price": 150.0,
                "Regime": "GREEN",
                "Type": "ISA_BUY",
                "Setup": "Trend Leader",
                "Stop Loss": 140.0,
                "Action": "Buy 100 Shares",
                "Metrics": "RSI:60",
                "Warning": ""
            }
        ]

        response = self.client.get('/screen/master?region=us')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['Ticker'], 'NVDA')
        self.assertEqual(data[0]['Regime'], 'GREEN')

if __name__ == '__main__':
    unittest.main()
