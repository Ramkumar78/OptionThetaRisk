import pytest
from unittest.mock import patch, MagicMock
from option_auditor.main_analyzer import refresh_dashboard_data

@patch("option_auditor.main_analyzer.fetch_live_prices")
def test_risk_map_generation(mock_fetch):
    # Mock live prices to be consistent
    mock_fetch.return_value = {"AAPL": 150.0, "TSLA": 200.0}

    saved_data = {
        "strategy_groups": [], # Not needed for risk map but required for function
        "open_positions": [
            # 1. Long Call ITM: Strike 100, Price 150. Moneyness (150-100)/100 = 0.5. Pnl_pct = 50.0
            {
                "symbol": "AAPL", "qty_open": 1, "contract": "C 100.0",
                "avg_price": 10.0, "dte": 30, "expiry": "2023-12-31"
            },
            # 2. Long Put OTM: Strike 100, Price 150. Moneyness (100-150)/100 = -0.5. Pnl_pct = -50.0
            {
                "symbol": "AAPL", "qty_open": 1, "contract": "P 100.0",
                "avg_price": 5.0, "dte": 30, "expiry": "2023-12-31"
            },
            # 3. Short Call OTM: Strike 200, Price 150. Moneyness (150-200)/200 = -0.25. Pnl_pct = 25.0 (since Short, -moneyness?)
            # Logic: if qty > 0: pnl_proxy = moneyness * 100 else: pnl_proxy = -moneyness * 100
            # Moneyness for Call: (cp - strike) / strike = (150 - 200) / 200 = -0.25
            # Qty < 0 (Short): -(-0.25) * 100 = 25.0
            {
                "symbol": "AAPL", "qty_open": -1, "contract": "C 200.0",
                "avg_price": 2.0, "dte": 30, "expiry": "2023-12-31"
            },
            # 4. Short Put ITM: Strike 200, Price 150. Moneyness (200 - 150) / 200 = 0.25
            # Qty < 0: -(0.25) * 100 = -25.0
            {
                "symbol": "AAPL", "qty_open": -1, "contract": "P 200.0",
                "avg_price": 15.0, "dte": 30, "expiry": "2023-12-31"
            },
            # 5. Invalid Contract String
            {
                "symbol": "AAPL", "qty_open": 1, "contract": "INVALID",
                "avg_price": 1.0, "dte": 30, "expiry": "2023-12-31"
            },
            # 6. Size Calculation Check: qty=2, avg_price=5.0 -> 2 * 100 * 5.0 = 1000.0
            {
                "symbol": "TSLA", "qty_open": 2, "contract": "C 200.0",
                "avg_price": 5.0, "dte": 30, "expiry": "2023-12-31"
            }
        ]
    }

    result = refresh_dashboard_data(saved_data)
    risk_map = result["risk_map"]

    assert len(risk_map) == 6

    # 1. Long Call ITM
    assert risk_map[0]["symbol"] == "AAPL"
    assert risk_map[0]["pnl_pct"] == 50.0

    # 2. Long Put OTM
    assert risk_map[1]["pnl_pct"] == -50.0

    # 3. Short Call OTM
    assert risk_map[2]["pnl_pct"] == 25.0

    # 4. Short Put ITM
    assert risk_map[3]["pnl_pct"] == -25.0

    # 5. Invalid Contract String -> pnl_pct should be 0.0 (default initialized)
    assert risk_map[4]["pnl_pct"] == 0.0

    # 6. Size Calculation
    # Size = abs(qty) * 100 * avg_price = 2 * 100 * 5.0 = 1000.0
    assert risk_map[5]["size"] == 1000.0
    assert risk_map[5]["symbol"] == "TSLA"
