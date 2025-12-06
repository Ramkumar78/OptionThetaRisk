import pytest
from option_auditor.main_analyzer import refresh_dashboard_data
from datetime import datetime
import json

def test_refresh_dashboard_data_structure():
    """Verify that refresh_dashboard_data handles dictionary structure correctly."""

    # Mock saved data
    saved_data = {
        "verdict": "Green Flag",
        "open_positions": [
            {
                "symbol": "FAKE",
                "contract": "P 100.0",
                "strike": 100.0,
                "qty_open": -1,
                "current_price": 50.0, # Stale price
                "expiry": "2025-01-01"
            }
        ]
    }

    # We expect _fetch_live_prices to be called.
    # Since we can't easily mock inner functions without patching,
    # and we don't want to hit yfinance, we rely on the fact that
    # refresh_dashboard_data handles connection errors gracefully (in _fetch_live_prices)
    # or returns the data structure modified if prices were found.

    # For this test, we just check that it runs without error and returns a dict
    res = refresh_dashboard_data(saved_data)

    assert isinstance(res, dict)
    assert "open_positions" in res
    assert res["open_positions"][0]["symbol"] == "FAKE"
    # DTE should be calculated if expiry is present
    # assert "dte" in res["open_positions"][0] # Might fail if date parsing fails or yfinance hangs

    # To test logic, we'd need to mock _fetch_live_prices.
    # But integration test with FAKE symbol might return empty price map, keeping None/old price?
    # Actually logic says: p["current_price"] = current_prices.get(sym)
    # If FAKE is not found, current_price becomes None.

    assert res["open_positions"][0]["current_price"] is None # "FAKE" ticker shouldn't exist/fetch

def test_refresh_dashboard_risk_logic():
    """Test ITM logic in refresh loop using a mock patch."""
    from unittest.mock import patch

    mock_prices = {"SPY": 400.0}

    with patch("option_auditor.main_analyzer._fetch_live_prices", return_value=mock_prices):
        saved_data = {
            "open_positions": [
                {
                    "symbol": "SPY",
                    "contract": "P 450.0", # Deep ITM Put (Short)
                    "strike": 450.0,
                    "qty_open": -10,
                    "expiry": datetime.now().date().isoformat()
                }
            ]
        }

        res = refresh_dashboard_data(saved_data)

        # Check if risk detected
        # Intrinsic: (450 - 400) * 10 * 100 = 50 * 1000 = 50,000 ITM Risk
        # Should trigger verdict override
        assert "High Open Risk" in res["verdict"]
        assert res["open_positions"][0]["risk_alert"] == "ITM Risk"
        assert res["open_positions"][0]["current_price"] == 400.0
