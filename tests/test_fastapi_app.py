from fastapi.testclient import TestClient
from webapp.main import app
import pytest
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "fastapi-core"}

@patch("option_auditor.screener.screen_trend_followers_isa")
def test_check_isa_stock_success(mock_screen):
    # Mock return data
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 150.0,
        "signal": "ENTER LONG",
        "trailing_exit_20d": 140.0
    }]

    payload = {"ticker": "AAPL", "entry_price": 145.0}
    response = client.post("/api/screen/isa/check", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["ticker"] == "AAPL"
    assert data["data"]["pnl_value"] == 5.0
    # Verify signal override logic
    assert "HOLD" in data["data"]["signal"]

@patch("option_auditor.screener.screen_trend_followers_isa")
def test_check_isa_stock_no_data(mock_screen):
    mock_screen.return_value = []

    payload = {"ticker": "INVALID"}
    response = client.post("/api/screen/isa/check", json=payload)

    assert response.status_code == 404
