import json
import pytest
from unittest.mock import patch, MagicMock
from webapp.app import create_app
import os

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_api_endpoints_return_json(client):
    """Verify that screeners return JSON instead of HTML."""

    # Mock data for screeners
    mock_market_data = [{"ticker": "AAPL", "price": 150.0}]
    mock_sector_data = [{"name": "Tech", "ticker": "XLK", "price": 100.0}]

    with patch('option_auditor.screener.screen_market', return_value=mock_market_data) as mock_screen, \
         patch('option_auditor.screener.screen_sectors', return_value=mock_sector_data) as mock_sectors:

        # Market Screener
        resp = client.post("/screen", data={"iv_rank": 50})
        assert resp.status_code == 200
        assert resp.is_json
        data = resp.json
        assert "results" in data
        assert "sector_results" in data
        assert data["results"] == mock_market_data
        assert data["sector_results"] == mock_sector_data

    with patch('option_auditor.screener.screen_turtle_setups', return_value=[]) as mock_turtle:
        # Turtle Screener
        resp = client.get("/screen/turtle")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json == []

    with patch('option_auditor.screener.screen_5_13_setups', return_value=[]) as mock_ema:
        # EMA Screener
        resp = client.get("/screen/ema")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json == []

def test_journal_api_crud(client):
    """Test Journal CRUD API."""
    # List (empty initially)
    resp = client.get("/journal")
    assert resp.status_code == 200
    assert resp.json == []

    # Add
    entry = {
        "symbol": "AAPL",
        "strategy": "Long Call",
        "sentiment": "Bullish",
        "notes": "Testing",
        "pnl": 100,
        "entry_date": "2023-01-01", # Required by schema implicitly or helps debugging
        "entry_time": "12:00",
        "direction": "Long",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "qty": 1
    }
    resp = client.post("/journal/add", json=entry)
    assert resp.status_code == 200
    assert resp.json["success"] is True
    entry_id = resp.json["id"]

    # List (should have one)
    resp = client.get("/journal")
    assert len(resp.json) == 1
    assert resp.json[0]["symbol"] == "AAPL"

    # Analyze
    # Mock journal analyzer
    with patch('option_auditor.journal_analyzer.analyze_journal', return_value={"mock_analysis": True}) as mock_analyze:
        resp = client.post("/journal/analyze")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json == {"mock_analysis": True}

    # Delete
    resp = client.delete(f"/journal/delete/{entry_id}")
    assert resp.status_code == 200
    assert resp.json["success"] is True

    # List (empty again)
    resp = client.get("/journal")
    assert len(resp.json) == 0

def test_analyze_api_returns_json(client):
    """Verify analyze endpoint returns JSON."""
    # We won't upload a real file as that invokes complex logic, but we can test validation errors return JSON
    resp = client.post("/analyze")
    assert resp.status_code == 400
    assert resp.is_json
    assert "error" in resp.json
