
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import screen_quantum_setups, get_cached_market_data

def test_quantum_fallback_and_nan():
    """
    Tests that screen_quantum_setups:
    1. Falls back to fetch_batch_data_safe if get_cached_market_data fails.
    2. Handles NaNs in calculation results (JSON serialization check).
    """

    # 1. Setup Mock for Failure of Cache
    with patch('option_auditor.screener.get_cached_market_data', side_effect=Exception("Cache Missing")):
        with patch('option_auditor.screener.fetch_batch_data_safe') as mock_fetch:
             # Create mock data with NaNs to test serialization
             dates = pd.date_range(start='2023-01-01', periods=250)
             df = pd.DataFrame({
                 'Close': np.random.rand(250) * 100,
                 'High': np.random.rand(250) * 105,
                 'Low': np.random.rand(250) * 95,
                 'Open': np.random.rand(250) * 100,
                 'Volume': np.random.randint(100, 1000, 250)
             }, index=dates)

             # Mock MultiIndex return
             mock_data = pd.concat([df], keys=['AAPL'], axis=1)
             mock_fetch.return_value = mock_data

             # Mock QuantPhysicsEngine to return NaNs
             # Must patch where it is IMPORTED (screener.py), not where it is defined
             with patch('option_auditor.screener.QuantPhysicsEngine') as MockEngine:
                 MockEngine.calculate_hurst.return_value = float('nan')
                 MockEngine.shannon_entropy.return_value = float('inf') # Test Infinity too
                 MockEngine.kalman_filter.return_value = pd.Series([100]*250) # Need series for slope calc
                 MockEngine.instantaneous_phase.return_value = float('nan')

                 results = screen_quantum_setups(ticker_list=['AAPL'], region='us')

                 # ASSERT FALLBACK HAPPENED
                 mock_fetch.assert_called_once()

                 # ASSERT SANITIZATION
                 if not results:
                     # It might return empty if everything filtered out or errored
                     # But we expect at least one result if not filtered by logic
                     # The logic requires len > 200, which we have.
                     # However, generate_human_verdict handles NaNs?
                     # Let's check if it crashed.
                     pass

                 assert len(results) == 1
                 res = results[0]
                 assert res['hurst'] is None
                 assert res['entropy'] is None
                 # Check JSON serializability
                 import json
                 try:
                     json.dumps(res)
                 except ValueError as e:
                     pytest.fail(f"JSON Serialization Failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__])
