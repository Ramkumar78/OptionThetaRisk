import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import json
from webapp.app import create_app

class TestApiQuant(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    @patch('webapp.app.QuantMasterScreener')
    def test_screen_quant_success(self, MockScreener):
        # Setup Mock
        mock_instance = MockScreener.return_value

        # Mock DF return
        mock_df = pd.DataFrame({
            'Ticker': ['AAPL', 'MSFT'],
            'Price': [150.0, 300.0],
            'ML_Prob_Up': [0.75, 0.65],
            'annualized_volatility': [0.2, 0.15]
        })
        mock_instance.run_screen.return_value = mock_df

        # Call Endpoint
        response = self.client.get('/screen/quant?region=us')

        # Verify
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['Ticker'], 'AAPL')
        self.assertEqual(data[0]['ML_Prob_Up'], 0.75)

    @patch('webapp.app.QuantMasterScreener')
    def test_screen_quant_empty(self, MockScreener):
        mock_instance = MockScreener.return_value
        mock_instance.run_screen.return_value = pd.DataFrame()

        response = self.client.get('/screen/quant')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data, [])

    @patch('webapp.app.QuantMasterScreener')
    def test_screen_quant_error(self, MockScreener):
        mock_instance = MockScreener.return_value
        mock_instance.run_screen.side_effect = Exception("OpenBB Failure")

        response = self.client.get('/screen/quant')
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn("error", data)
