import pytest
import json
import uuid
import time
import io
from unittest.mock import patch, MagicMock, ANY
from webapp.app import create_app

@pytest.fixture
def app():
    app = create_app(testing=True)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_storage():
    """Patches _get_storage_provider in journal_routes to return a mock storage object."""
    with patch('webapp.blueprints.journal_routes._get_storage_provider') as mock_get_provider:
        mock_storage_obj = MagicMock()
        mock_get_provider.return_value = mock_storage_obj
        yield mock_storage_obj

def test_journal_add_entry_success(client, mock_storage):
    """Test successful addition of a manual journal entry."""
    mock_storage.save_journal_entry.return_value = "entry_123"

    payload = {
        "symbol": "AAPL",
        "strategy": "long_call",
        "pnl": 150.0,
        "notes": "Good trade",
        "emotions": ["happy", "confident"]
    }

    response = client.post('/journal/add', json=payload)

    assert response.status_code == 200
    assert response.json == {"success": True, "id": "entry_123"}

    # Verify storage call
    mock_storage.save_journal_entry.assert_called_once()
    args, _ = mock_storage.save_journal_entry.call_args
    saved_data = args[0]
    assert saved_data['symbol'] == "AAPL"
    assert saved_data['pnl'] == 150.0
    assert saved_data['username'] is not None  # Guest session created
    assert 'created_at' in saved_data

def test_journal_add_entry_validation_error(client, mock_storage):
    """Test validation error when adding an invalid journal entry."""
    # Sending invalid types to trigger Pydantic validation error
    payload = {
        "pnl": "not_a_number"
    }

    response = client.post('/journal/add', json=payload)

    assert response.status_code == 400
    assert response.json['error'] == "Validation Error"

    # Verify storage was NOT called
    mock_storage.save_journal_entry.assert_not_called()

def test_journal_get_entries_success(client, mock_storage):
    """Test retrieving journal entries."""
    mock_entries = [
        {"id": "1", "symbol": "AAPL", "pnl": 100},
        {"id": "2", "symbol": "GOOG", "pnl": -50}
    ]
    mock_storage.get_journal_entries.return_value = mock_entries

    response = client.get('/journal')

    assert response.status_code == 200
    assert response.json == mock_entries
    mock_storage.get_journal_entries.assert_called_once()

def test_journal_delete_entry_success(client, mock_storage):
    """Test deleting a journal entry."""
    response = client.delete('/journal/delete/entry_123')

    assert response.status_code == 200
    assert response.json == {"success": True}

    # Verify call with ANY username since guest session is created
    mock_storage.delete_journal_entry.assert_called_once_with(ANY, "entry_123")

def test_journal_import_trades_success(client, mock_storage):
    """Test importing trades successfully."""
    mock_storage.save_journal_entries.return_value = 2

    # Payload matching JournalImportRequest (List[Dict])
    payload = [
        {
            "symbol": "AAPL",
            "strategy": "iron_condor",
            "pnl": 200.0,
            "segments": [{"entry_ts": "2023-10-27T10:00:00"}]
        },
        {
            "symbol": "MSFT",
            "pnl": -50.0
            # Missing segments, should use fallback date
        }
    ]

    response = client.post('/journal/import', json=payload)

    assert response.status_code == 200
    assert response.json == {"success": True, "count": 2}

    mock_storage.save_journal_entries.assert_called_once()
    args, _ = mock_storage.save_journal_entries.call_args
    entries = args[0]
    assert len(entries) == 2
    assert entries[0]['entry_date'] == "2023-10-27"
    assert entries[0]['entry_time'] == "10:00:00"
    # The second entry should use the current date fallback
    assert entries[1]['entry_date'] is not None

def test_journal_import_trades_invalid_date_fallback(client, mock_storage):
    """Test import with invalid date format falling back to current date."""
    mock_storage.save_journal_entries.return_value = 1

    payload = [{
        "symbol": "TSLA",
        "segments": [{"entry_ts": "invalid-date-format"}]
    }]

    response = client.post('/journal/import', json=payload)

    assert response.status_code == 200
    entries = mock_storage.save_journal_entries.call_args[0][0]
    assert entries[0]['entry_date'] is not None  # Should be current date
    # Verify it didn't crash

def test_journal_import_trades_empty(client, mock_storage):
    """Test importing an empty list of trades."""
    mock_storage.save_journal_entries.return_value = 0

    response = client.post('/journal/import', json=[])

    assert response.status_code == 200
    assert response.json == {"success": True, "count": 0}
    mock_storage.save_journal_entries.assert_called_with([])

def test_journal_import_trades_validation_error(client, mock_storage):
    """Test validation error for import endpoint."""
    # Sending a dict instead of a list
    response = client.post('/journal/import', json={"not": "a list"})

    assert response.status_code == 400
    assert response.json['error'] == "Validation Error"
    mock_storage.save_journal_entries.assert_not_called()

def test_journal_import_security_no_file_upload(client, mock_storage):
    """
    Security Test: Verify that sending a file upload (multipart/form-data)
    to the JSON-expecting import endpoint results in a 400 error.
    This ensures no unintended file processing occurs.
    """
    data = {
        'file': (io.BytesIO(b"dummy content"), 'test.csv')
    }
    # Flask test client content_type defaults to multipart/form-data when data is a dict with file
    response = client.post('/journal/import', data=data, content_type='multipart/form-data')

    # Should be 400 because validate_schema expects JSON and gets None/Empty or fails parsing form as JSON
    assert response.status_code == 400
    # The validation decorator tries request.get_json(silent=True) which returns None for multipart
    # Then it calls schema(None/Empty) which fails validation for List
    assert response.json['error'] == "Validation Error" or response.json['error'] == "Invalid request"
    mock_storage.save_journal_entries.assert_not_called()

def test_journal_analyze_batch_success(client, mock_storage):
    """Test analyzing journal entries."""
    mock_entries = [{"id": "1", "pnl": 100}]
    mock_storage.get_journal_entries.return_value = mock_entries

    expected_result = {"win_rate": 1.0, "total_pnl": 100}

    with patch('webapp.blueprints.journal_routes.journal_analyzer.analyze_journal') as mock_analyze:
        mock_analyze.return_value = expected_result

        response = client.post('/journal/analyze')

        assert response.status_code == 200
        assert response.json == expected_result

        mock_storage.get_journal_entries.assert_called_once()
        mock_analyze.assert_called_once_with(mock_entries)

def test_journal_export_csv_success(client, mock_storage):
    """Test exporting journal to CSV."""
    mock_entries = [
        {"entry_date": "2023-01-01", "entry_time": "10:00", "symbol": "AAPL", "strategy": "call", "sentiment": "bullish", "pnl": 100, "notes": "note1"},
        {"entry_date": "2023-01-02", "entry_time": "11:00", "symbol": "GOOG", "strategy": "put", "sentiment": "bearish", "pnl": -50, "notes": "note2"}
    ]
    mock_storage.get_journal_entries.return_value = mock_entries

    response = client.get('/api/journal/export')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'] == 'attachment; filename=journal_export.csv'

    csv_content = response.data.decode('utf-8')
    assert "entry_date,entry_time,symbol,strategy,sentiment,pnl,notes" in csv_content or "entry_date" in csv_content
    assert "AAPL" in csv_content
    assert "GOOG" in csv_content
    assert "100" in csv_content
    assert "-50" in csv_content

def test_journal_export_csv_empty(client, mock_storage):
    """Test exporting empty journal."""
    mock_storage.get_journal_entries.return_value = []

    response = client.get('/api/journal/export')

    assert response.status_code == 200
    csv_content = response.data.decode('utf-8')
    # Should at least contain headers
    assert "entry_date" in csv_content
    assert "symbol" in csv_content
