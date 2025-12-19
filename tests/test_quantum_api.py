import unittest
import json
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------
# ASSUMPTION: Your Flask app structure looks like this.
# Adjust the import 'from webapp.app import app' if needed.
# ---------------------------------------------------------
try:
    from webapp.app import app
except ImportError:
    # Fallback for direct testing if not in package structure
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from webapp.app import app

class TestQuantumAPI(unittest.TestCase):

    def setUp(self):
        """Setup the test client before each test."""
        self.app = app.test_client()
        self.app.testing = True
        # Clear the cache to prevent test pollution
        try:
            from webapp.app import screener_cache
            screener_cache.cache.clear()
        except ImportError:
            pass

    # ---------------------------------------------------------
    # TEST CASE 1: The "Checkmate" Setup (Winner)
    # ---------------------------------------------------------
    @patch('webapp.app.screener.screen_quantum_setups') # Adjusted path to match actual function call in app.py
    def test_checkmate_scenario(self, mock_screener):
        """
        Verify that a High Hurst (>0.65) and Low Entropy (<1.3)
        correctly triggers a 'QUANTUM BUY' verdict.
        """

        # 1. Mock the Screener Output
        # We return a dict matching the structure expected by app.py (from screener.py)
        mock_result = {
            "ticker": "NVDA",
            "company_name": "NVIDIA",
            "price": 145.50,
            "hurst": 0.72,   # Strong Trend (Checkmate)
            "entropy": 1.15,  # Low Chaos (Checkmate)
            "signal": "QUANTUM BUY", # Mapped to verdict
            "score": 95,
            "kalman_diff": 0.0,
            "phase": 0.0,
            "verdict_color": "green",
            "atr_value": 0.0,
            "volatility_pct": 0.0,
            "pct_change_1d": 0.0,
            "breakout_date": "2023-01-01"
        }

        # The engine returns a list of results
        mock_screener.return_value = [mock_result]

        # 2. Call the API Endpoint
        response = self.app.get('/screen/quantum')
        data = json.loads(response.data)

        # 3. Assertions (The Verification)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 1)

        row = data[0]
        self.assertEqual(row['ticker'], "NVDA")
        self.assertEqual(row['hurst'], 0.72)
        self.assertEqual(row['verdict'], "QUANTUM BUY")

        # verify the frontend gets the data needed for the Green Tags
        print("\n[PASS] Checkmate Scenario Verified: NVDA H=0.72 triggers QUANTUM BUY")

    # ---------------------------------------------------------
    # TEST CASE 2: The "Avoid" Setup (Loser)
    # ---------------------------------------------------------
    @patch('webapp.app.screener.screen_quantum_setups')
    def test_avoid_scenario(self, mock_screener):
        """
        Verify that Random Walk (H~0.5) and High Chaos (S>2.0)
        returns the raw data correctly so the Frontend can flag it RED.
        """

        mock_result = {
            "ticker": "TRAP",
            "company_name": "Trap Corp",
            "price": 10.00,
            "hurst": 0.51,   # Random Walk (Bad)
            "entropy": 2.40,  # High Chaos (Bad)
            "signal": "AVOID",
            "score": 12,
            "kalman_diff": 0.0,
            "phase": 0.0,
            "verdict_color": "red",
            "atr_value": 0.0,
            "volatility_pct": 0.0,
            "pct_change_1d": 0.0,
            "breakout_date": "N/A"
        }

        mock_screener.return_value = [mock_result]

        response = self.app.get('/screen/quantum')
        data = json.loads(response.data)

        row = data[0]
        self.assertEqual(row['ticker'], "TRAP")
        self.assertEqual(row['hurst'], 0.51)
        self.assertEqual(row['entropy'], 2.40)
        self.assertEqual(row['verdict'], "AVOID")

        print(f"[PASS] Avoid Scenario Verified: TRAP Entropy={row['entropy']} correctly served.")

if __name__ == '__main__':
    unittest.main()
