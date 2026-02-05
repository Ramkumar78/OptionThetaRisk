import pytest
from unittest.mock import MagicMock, patch
from option_auditor.main_analyzer import analyze_csv, refresh_dashboard_data
from option_auditor.risk_analyzer import calculate_discipline_score

# Mock strategy class for direct testing of helper
class MockStrategy:
    def __init__(self, net_pnl, hold_days, is_revenge=False):
        self.net_pnl = net_pnl
        self._hold_days = hold_days
        self.is_revenge = is_revenge
        self.strategy_name = "Test"
        self.symbol = "TEST"
        self.expiry = None # Added for compatibility if accessed
        self.legs = [] # Added
        self.segments = [] # Added
        self.pnl = net_pnl # Gross pnl
        self.fees = 0.0

    def hold_days(self):
        return self._hold_days

    def average_daily_pnl(self):
        return 0.0

def test_calculate_discipline_score():
    # Case 1: Perfect score
    strats = [MockStrategy(100, 5), MockStrategy(-50, 1)] # Loss cut early (1 < 5*0.5? No, avg=3. 1 < 1.5? Yes)
    # Avg hold = (5+1)/2 = 3. 0.5*3 = 1.5. 1 < 1.5. So +Bonus.
    open_pos = [{"dte": 10}]
    score, details = calculate_discipline_score(strats, open_pos)
    # Start 100. Bonus +2 (min 20, count 1 * 2 = 2). Score 102 -> 100.
    assert score == 100

    # Case 2: Revenge trade
    strats = [MockStrategy(-100, 5, is_revenge=True)]
    open_pos = []
    score, details = calculate_discipline_score(strats, open_pos)
    # Start 100. Revenge -10. Score 90.
    assert score == 90
    assert any("Revenge" in d for d in details)

    # Case 3: Gamma Risk
    strats = []
    open_pos = [{"dte": 2}]
    score, details = calculate_discipline_score(strats, open_pos)
    # Start 100. Gamma -5. Score 95.
    assert score == 95
    assert any("Gamma" in d for d in details)

@patch("option_auditor.main_analyzer.fetch_live_prices")
def test_analyze_csv_returns_new_fields(mock_fetch):
    mock_fetch.return_value = {"AAPL": 150.0}

    # Manual data input compliant with ManualInputParser
    manual_data = [
        {
            "symbol": "AAPL", "date": "2023-01-01", "action": "BOT",
            "qty": 1, "price": 100, "fees": 1.0, "amount": -101.0,
            "description": "Stock", "expiry": None, "strike": None, "right": None
        }
    ]

    result = analyze_csv(manual_data=manual_data)

    assert "discipline_score" in result
    assert "risk_map" in result
    assert isinstance(result["risk_map"], list)

@patch("option_auditor.main_analyzer.fetch_live_prices")
def test_refresh_dashboard_data_structure(mock_fetch):
    mock_fetch.return_value = {"AAPL": 160.0}

    saved_data = {
        "strategy_groups": [
            {"is_revenge": False, "pnl": 100, "hold_days": 5}
        ],
        "open_positions": [
            {"symbol": "AAPL", "qty_open": 1, "contract": "Stock", "expiry": None}
        ]
    }

    result = refresh_dashboard_data(saved_data)

    assert "discipline_score" in result
    assert "risk_map" in result
    assert isinstance(result["risk_map"], list)
