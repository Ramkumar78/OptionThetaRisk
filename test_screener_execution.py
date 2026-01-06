import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_fourier_cycles, screen_dynamic_volatility_fortress, screen_quantum_setups

class TestScreenerExecution(unittest.TestCase):
    @patch('option_auditor.screener.fetch_batch_data_safe')
    @patch('option_auditor.screener.get_cached_market_data')
    def test_screeners_run(self, mock_cached, mock_batch):
        # Mock DataFrame
        dates = pd.date_range('2023-01-01', periods=200)
        df = pd.DataFrame({
            'Open': np.linspace(100, 150, 200),
            'High': np.linspace(105, 155, 200),
            'Low': np.linspace(95, 145, 200),
            'Close': np.linspace(100, 150, 200),
            'Volume': [1000000]*200
        }, index=dates)

        # Mock multi-index return for batch
        mock_data = pd.concat([df], axis=1, keys=['AAPL'])
        mock_batch.return_value = mock_data
        mock_cached.return_value = mock_data

        # Patch LIQUID_OPTION_TICKERS locally if needed, but we pass ticker list

        # Test Fourier
        print("Testing Fourier...")
        res = screen_fourier_cycles(ticker_list=['AAPL'])
        self.assertTrue(len(res) > 0, "Fourier returned empty")
        self.assertIn('breakout_date', res[0])

        # Test Fortress
        # Fortress calls get_cached_market_data internally
        print("Testing Fortress...")
        with patch('option_auditor.screener._get_market_regime', return_value=15.0):
             res = screen_dynamic_volatility_fortress(ticker_list=['AAPL'])
             self.assertTrue(len(res) > 0, "Fortress returned empty")
             self.assertIn('breakout_date', res[0])

        # Test Quantum
        print("Testing Quantum...")
        # Quantum needs specific mocks for physics engine or it returns None
        # But we just want to ensure it calls breakout_date without crashing
        with patch('option_auditor.quant_engine.QuantPhysicsEngine.calculate_hurst', return_value=0.7),              patch('option_auditor.quant_engine.QuantPhysicsEngine.shannon_entropy', return_value=0.5),              patch('option_auditor.quant_engine.QuantPhysicsEngine.kalman_filter', return_value=pd.Series([100]*200)),              patch('option_auditor.quant_engine.QuantPhysicsEngine.generate_human_verdict', return_value=("BUY", "Rationale")):

             res = screen_quantum_setups(ticker_list=['AAPL'])
             self.assertTrue(len(res) > 0, "Quantum returned empty")
             self.assertIn('breakout_date', res[0])

if __name__ == '__main__':
    unittest.main()
