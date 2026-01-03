
import sys
from unittest.mock import MagicMock

# Mock dependencies not available in the test env
sys.modules['pykalman'] = MagicMock()
sys.modules['pybreaker'] = MagicMock()
sys.modules['pandas_ta'] = MagicMock()
sys.modules['option_auditor.quant_engine'] = MagicMock()
sys.modules['option_auditor.sp500_data'] = MagicMock()
sys.modules['option_auditor.uk_stock_data'] = MagicMock()

# However, screener imports QuantPhysicsEngine from it.


import pytest
from option_auditor.screener import screen_quantum_setups

def test_screen_quantum_us_crash():
    """
    Attempts to run screen_quantum_setups(region='us') to reproduce the 500 error.
    """
    print("Running screen_quantum_setups(region='us')...")
    try:
        results = screen_quantum_setups(region="us")
        print(f"Success! Returned {len(results)} results.")
    except Exception as e:
        print(f"CAUGHT CRASH: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Crash detected: {e}")

if __name__ == "__main__":
    test_screen_quantum_us_crash()
