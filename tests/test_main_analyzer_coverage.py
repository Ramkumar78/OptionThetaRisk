import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from option_auditor import main_analyzer, models

# --- Test analyze_portfolio branches ---

# analyze_portfolio is NOT a function in main_analyzer.py.
# The main function is `analyze_csv`. I got confused by the function name in my memory or previous code.
# The code shows `analyze_csv`.

# So I should test `analyze_csv`.

@patch('option_auditor.main_analyzer.TastytradeFillsParser')
@patch('option_auditor.main_analyzer.build_strategies')
def test_analyze_csv_empty(mock_build, mock_parser_cls):
    # If parse returns empty
    mock_parser = MagicMock()
    mock_parser_cls.return_value = mock_parser
    mock_parser.parse.return_value = pd.DataFrame()

    # We need to bypass file reading or pass valid input
    manual_data = [{"symbol": "AAPL", "date": "2023-01-01", "action": "BUY", "qty": 1, "price": 100}]

    # But analyze_csv handles manual data by using ManualInputParser.
    # If we pass csv_path=None and manual_data=None, it returns error.

    res = main_analyzer.analyze_csv(None, "auto")
    assert "error" in res
    assert res["error"] == "No input data provided"

@patch('option_auditor.main_analyzer.build_strategies')
def test_analyze_csv_manual(mock_build):
    manual_data = [{
        "symbol": "AAPL",
        "date": "2023-01-01",
        "time": "10:00:00",
        "action": "BUY",
        "qty": 1,
        "price": 100
    }]

    # We need to patch ManualInputParser inside main_analyzer
    with patch('option_auditor.main_analyzer.ManualInputParser') as MockParser:
        mock_parser = MagicMock()
        MockParser.return_value = mock_parser

        # Mock parsed DF
        mock_parser.parse.return_value = pd.DataFrame({
            "contract_id": ["C1"],
            "symbol": ["AAPL"],
            "datetime": [pd.Timestamp("2023-01-01 10:00:00")],
            "qty": [1],
            "price": [100],
            "fees": [1.0],
            "proceeds": [-100],
            "expiry": [pd.NaT],
            "strike": [None],
            "right": [None]
        })

        mock_build.return_value = []

        res = main_analyzer.analyze_csv(None, "auto", manual_data=manual_data)
        assert "error" not in res
        assert "metrics" in res

# --- Test risk analysis (ITM, Gamma) ---

def test_itm_risk_logic():
    # Direct test of logic inside _generate_risk_alerts or similar if accessible
    # Or rely on analyze_portfolio with open positions
    pass

@patch('option_auditor.main_analyzer.yf.download')
def test_refresh_dashboard_data(mock_download):
    saved_data = {
        "summary": {"total_pnl": 100},
        "open_positions": [
            {
                "symbol": "AAPL",
                "contract_id": "AAPL:2025-01-01:C:150",
                "qty": 1,
                "avg_price": 5.0, # $500 cost
                "current_price": 0.0,
                "expiry": "2025-01-01",
                "strike": 150,
                "right": "C"
            }
        ],
        "verdict": {"color": "gray"}
    }

    # Mock Live Price
    # The function _fetch_live_prices is used. It handles yfinance download.
    # It returns a dict {symbol: price}.
    # We should patch _fetch_live_prices instead of yf.download to avoid complex DF mocking.
    pass # See below re-definition

@patch('option_auditor.main_analyzer._fetch_live_prices')
def test_refresh_dashboard_data_redefined(mock_fetch_prices):
    saved_data = {
        "summary": {"total_pnl": 100},
        "open_positions": [
            {
                "symbol": "AAPL",
                "contract_id": "AAPL:2025-01-01:C:150",
                "contract": "C 150.0", # Added missing field
                "qty_open": 1,         # Expected key is qty_open
                "avg_price": 5.0,
                "current_price": 0.0,
                "expiry": "2025-01-01",
                "strike": 150,
                "right": "C"
            }
        ],
        "verdict": {"color": "gray"}
    }

    mock_fetch_prices.return_value = {"AAPL": 155.0}

    updated = main_analyzer.refresh_dashboard_data(saved_data)

    pos = updated["open_positions"][0]
    assert pos["current_price"] == 155.0

    # ITM Risk: Strike 150 Call, Price 155 -> 5.0 ITM.
    # (155-150)/150 = 0.033 > 0.01 threshold.
    # Should be flagged.

    # The risk alert logic:
    # 1. Calculate Net Exposure per symbol.
    # AAPL: Long 1 Call 150. Intrinsic = (155-150)*100 = 500.
    # Net Exposure = 500.
    # Trigger condition: Net < -500. It is POSITIVE 500. So NO Global Risk Flag.

    # 2. If Global Risk Flag is FALSE, individual rows are NOT checked for "ITM Risk" label in this logic?
    # Checking code:
    # if itm_risk_flag and sym in current_prices: ...

    # So if I want to trigger ITM Risk, I need Net Exposure < -500.
    # Let's change position to Short Call ITM.

    pass

@patch('option_auditor.main_analyzer._fetch_live_prices')
def test_refresh_dashboard_data_risk(mock_fetch_prices):
    saved_data = {
        "summary": {"total_pnl": 100},
        "open_positions": [
            {
                "symbol": "AAPL",
                "contract_id": "AAPL:2025-01-01:C:140",
                "contract": "C 140.0",
                "qty_open": -5,         # Short 5 Calls
                "avg_price": 5.0,
                "current_price": 0.0,
                "expiry": "2025-01-01",
                "strike": 140.0,
                "right": "C"
            }
        ],
        "verdict": {"color": "gray"}
    }

    mock_fetch_prices.return_value = {"AAPL": 150.0}

    # Net Exposure:
    # Short 5 Calls strike 140. Price 150.
    # Intrinsic per call = max(0, 150-140) = 10.
    # Total Intrinsic = 10 * -5 * 100 = -5000.
    # -5000 < -500 -> Risky.

    updated = main_analyzer.refresh_dashboard_data(saved_data)

    pos = updated["open_positions"][0]
    assert "risk_alert" in pos
    assert pos["risk_alert"] == "ITM Risk"

    assert "High Open Risk" in updated["verdict"]

# analyze_portfolio is redundant here as analyze_csv IS the wrapper logic.
# I already tested analyze_csv above.
