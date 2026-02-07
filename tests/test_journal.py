import json
import pytest

def test_journal_routes_no_auth(client):
    """Test journal CRUD operations without authentication (relies on guest session)."""

    # 1. Add Entry
    new_entry = {
        "entry_date": "2025-01-01",
        "entry_time": "10:00",
        "symbol": "SPY",
        "strategy": "Iron Condor",
        "direction": "Short",
        "qty": 1,
        "entry_price": 1.50,
        "exit_price": 1.00,
        "pnl": 50.0,
        "notes": "Test Note"
    }

    resp_add = client.post("/api/journal/add", json=new_entry)
    assert resp_add.status_code == 200
    data_add = resp_add.get_json()
    assert data_add["success"] is True
    entry_id = data_add["id"]

    # 2. Get Entries
    resp_get = client.get("/api/journal")
    assert resp_get.status_code == 200
    entries = resp_get.get_json()
    assert len(entries) == 1
    assert entries[0]["id"] == entry_id
    assert entries[0]["symbol"] == "SPY"

    # 3. Analyze
    # Requires at least one entry, which we have.
    resp_analyze = client.post("/api/journal/analyze")
    assert resp_analyze.status_code == 200
    report = resp_analyze.get_json()
    assert "win_rate" in report

    # 4. Delete Entry
    resp_del = client.delete(f"/api/journal/delete/{entry_id}")
    assert resp_del.status_code == 200

    # Verify Empty
    resp_get_after = client.get("/api/journal")
    assert len(resp_get_after.get_json()) == 0

def test_journal_entry_with_emotions_and_notes(client):
    """Test adding and retrieving a journal entry with emotions and notes."""
    entry_data = {
        "entry_date": "2025-01-02",
        "entry_time": "11:00",
        "symbol": "QQQ",
        "strategy": "Long Call",
        "pnl": 100.0,
        "notes": "Feeling good about this trade.",
        "emotions": ["Disciplined", "Confident"]
    }

    # Add Entry
    resp_add = client.post("/api/journal/add", json=entry_data)
    assert resp_add.status_code == 200
    data_add = resp_add.get_json()
    assert data_add["success"] is True

    # Retrieve Entries
    resp_get = client.get("/api/journal")
    assert resp_get.status_code == 200
    entries = resp_get.get_json()

    # Find the entry
    target = next((e for e in entries if e["symbol"] == "QQQ"), None)
    assert target is not None
    assert target["notes"] == "Feeling good about this trade."
    assert set(target["emotions"]) == {"Disciplined", "Confident"}

    # Cleanup
    entry_id = target["id"]
    client.delete(f"/api/journal/delete/{entry_id}")
