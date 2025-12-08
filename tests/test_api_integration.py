import json
import pytest
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_api_endpoints_return_json(client):
    """Verify that screeners return JSON instead of HTML."""
    # Market Screener
    resp = client.post("/screen", data={"iv_rank": 50})
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.json
    assert "results" in data
    assert "sector_results" in data

    # Turtle Screener
    resp = client.get("/screen/turtle")
    assert resp.status_code == 200
    assert resp.is_json

    # EMA Screener
    resp = client.get("/screen/ema")
    assert resp.status_code == 200
    assert resp.is_json

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
    resp = client.post("/journal/analyze")
    assert resp.status_code == 200
    assert resp.is_json

    # Delete
    resp = client.delete(f"/journal/delete/{entry_id}")
    assert resp.status_code == 200
    assert resp.json["success"] is True

    # List (empty again)
    resp = client.get("/journal")
    assert len(resp.json) == 0

def test_root_serves_react(client):
    """Verify root path serves the React index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    # Should be the index.html from React build (which we copied to static/react_build)
    # Since we can't guarantee content in test env without build, we check minimal basic expectation
    # or just that it didn't crash.
    # In this env, if react_build is empty, it might fail or return 404/500 depending on implementation.
    # The 'index.html' string should be in the response content if it's finding the file we built earlier.
    # We verified building in previous steps.
    assert b"<!doctype html>" in resp.data.lower()

def test_analyze_api_returns_json(client):
    """Verify analyze endpoint returns JSON."""
    # We won't upload a real file as that invokes complex logic, but we can test validation errors return JSON
    resp = client.post("/analyze")
    assert resp.status_code == 400
    assert resp.is_json
    assert "error" in resp.json
