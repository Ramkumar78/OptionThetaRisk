import pytest
from unittest.mock import MagicMock, patch
from webapp.app import create_app

@pytest.fixture
def app():
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@patch("webapp.blueprints.analysis_routes.UnifiedBacktester")
def test_analyze_backtest_success(mock_ub_cls, client):
    # Setup Mock
    mock_instance = MagicMock()
    mock_ub_cls.return_value = mock_instance

    mock_result = {
        "ticker": "AAPL",
        "strategy": "MASTER",
        "trades": 5,
        "equity_curve": [{"date": "2023-01-01", "strategy_equity": 10500, "buy_hold_equity": 10200}]
    }
    mock_instance.run.return_value = mock_result

    # Send Request
    payload = {
        "ticker": "AAPL",
        "strategy": "master",
        "initial_capital": 10000
    }
    response = client.post("/analyze/backtest", json=payload)

    # Assertions
    assert response.status_code == 200
    data = response.get_json()
    assert data["ticker"] == "AAPL"
    assert "equity_curve" in data

    # Verify Mock Call
    mock_ub_cls.assert_called_with("AAPL", strategy_type="master", initial_capital=10000.0)
    mock_instance.run.assert_called_once()

@patch("webapp.blueprints.analysis_routes.UnifiedBacktester")
def test_analyze_backtest_missing_ticker(mock_ub_cls, client):
    payload = {
        "strategy": "master"
    }
    response = client.post("/analyze/backtest", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Validation Error" in data["error"]
    assert any("ticker" in str(d["loc"]) for d in data["details"])

@patch("webapp.blueprints.analysis_routes.UnifiedBacktester")
def test_analyze_backtest_backend_error(mock_ub_cls, client):
    mock_instance = MagicMock()
    mock_ub_cls.return_value = mock_instance
    mock_instance.run.return_value = {"error": "No data found"}

    payload = {
        "ticker": "BADTICKER"
    }
    response = client.post("/analyze/backtest", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No data found" in data["error"]

@patch("webapp.blueprints.analysis_routes.UnifiedBacktester")
def test_analyze_backtest_invalid_capital(mock_ub_cls, client):
    payload = {
        "ticker": "AAPL",
        "initial_capital": "NOT_A_NUMBER"
    }
    response = client.post("/analyze/backtest", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "Validation Error" in data["error"]
    assert any("initial_capital" in str(d["loc"]) for d in data["details"])
