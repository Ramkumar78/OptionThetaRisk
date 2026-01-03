import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_quantum_setups

class TestQuantumScreenerCalculations(unittest.TestCase):

    @patch('option_auditor.screener.get_cached_market_data')
    @patch('option_auditor.screener.fetch_batch_data_safe')
    @patch('option_auditor.screener.QuantPhysicsEngine')
    def test_risk_management_calculations(self, mock_engine, mock_fetch, mock_cache):
        # Setup Mock Data
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')

        # Create a dataframe where High-Low is exactly 10, and Close is constant.
        # TR will be 10 every day. So ATR(any) will be 10.
        df = pd.DataFrame(index=dates)
        df['Close'] = 100.0
        df['Open'] = 100.0
        df['High'] = 105.0
        df['Low'] = 95.0
        df['Volume'] = 1000000

        # Setup MultiIndex DataFrame as expected by screener
        cols = pd.MultiIndex.from_product([['TEST'], ['Close', 'Open', 'High', 'Low', 'Volume']])
        data = pd.DataFrame(index=dates, columns=cols)
        for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
            data[('TEST', col)] = df[col]

        mock_cache.return_value = data
        mock_fetch.return_value = data

        # Mock QuantPhysicsEngine to return values triggering a BUY
        mock_engine.calculate_hurst.return_value = 0.8
        mock_engine.shannon_entropy.return_value = 0.5
        # Provide dummy series for kalman/breakout
        mock_engine.kalman_filter.return_value = pd.Series([100]*250)
        mock_engine.instantaneous_phase.return_value = 0.0
        mock_engine.analyze_breakout.return_value = {}

        # Force a "BUY" verdict so we check the Long logic
        mock_engine.generate_human_verdict.return_value = ("BUY (🔥 Strong)", "Test Rationale")

        # Run Screener
        # Use simple list to avoid resolving region tickers if we mock cache
        results = screen_quantum_setups(ticker_list=['TEST'], region='us')

        self.assertEqual(len(results), 1)
        res = results[0]

        atr = res['ATR']
        price = res['price']
        target = res['Target']
        stop = res['Stop Loss']

        # Verify ATR is approx 10
        self.assertAlmostEqual(atr, 10.0, places=1)

        # Verify Stop Loss: Price - 2.5 * ATR (New Requirement)
        self.assertAlmostEqual(stop, price - 2.5 * atr, places=2)

        # Verify Target Price: Price + 4.0 * ATR (New Requirement)
        self.assertAlmostEqual(target, price + 4.0 * atr, places=2)

if __name__ == '__main__':
    unittest.main()
