import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import json
from webapp.app import create_app

class TestApiQuant(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.client = self.app.test_client()

    @patch('webapp.blueprints.screener_routes.screen_master_convergence')
    def test_screen_quant_redirects_to_master_logic(self, mock_logic):
        # Mock underlying logic since screen_master is a local function
        mock_logic.return_value = [{"ticker": "AAPL", "confluence_score": 3}]

        # Call Endpoint
        response = self.client.get('/screen/quant?region=us')

        # Verify
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]['ticker'], 'AAPL')
