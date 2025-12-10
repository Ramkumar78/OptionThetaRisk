import os
import pytest
import sqlite3
import uuid
from unittest.mock import MagicMock, patch
from webapp.storage import PostgresStorage, S3Storage, get_storage_provider, StorageProvider
from webapp.sqlite_storage import LocalStorage

# --- Tests for LocalStorage (SQLite) ---

@pytest.fixture
def local_storage(tmp_path):
    db_path = tmp_path / "test.db"
    return LocalStorage(str(db_path))

def test_local_storage_init(local_storage):
    assert os.path.exists(local_storage.db_path)
    # Check tables exist
    with sqlite3.connect(local_storage.db_path) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        assert "reports" in table_names
        assert "users" in table_names
        assert "feedback" in table_names
        assert "portfolios" in table_names
        assert "journal_entries" in table_names

def test_local_storage_report(local_storage):
    token = "test_token"
    filename = "test.pdf"
    data = b"test content"

    local_storage.save_report(token, filename, data)
    fetched_data = local_storage.get_report(token, filename)
    assert fetched_data == data

    # Non-existent report
    assert local_storage.get_report("bad", "bad") is None

def test_local_storage_cleanup_reports(local_storage):
    token = "test_token"
    filename = "test.pdf"
    data = b"test content"

    # Insert with explicit time.time() call
    with patch("time.time") as mock_time:
        mock_time.return_value = 1000.0
        local_storage.save_report(token, filename, data)

    # Verify exist
    assert local_storage.get_report(token, filename) == data

    # Cleanup with cutoff before 1000.0 (e.g., current time 1100, retention 200 -> cutoff 900)
    # Should NOT delete
    with patch("time.time") as mock_time:
        mock_time.return_value = 1100.0
        local_storage.cleanup_old_reports(200) # Cutoff 900 < 1000
    assert local_storage.get_report(token, filename) == data

    # Cleanup with cutoff after 1000.0 (e.g., current time 1100, retention 50 -> cutoff 1050)
    # Should delete
    with patch("time.time") as mock_time:
        mock_time.return_value = 1100.0
        local_storage.cleanup_old_reports(50) # Cutoff 1050 > 1000

    assert local_storage.get_report(token, filename) is None

def test_local_storage_user(local_storage):
    user_data = {
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User"
    }
    local_storage.save_user(user_data)

    fetched = local_storage.get_user("testuser")
    assert fetched["username"] == "testuser"
    assert fetched["first_name"] == "Test"

    # Update
    user_data["first_name"] = "Updated"
    local_storage.save_user(user_data)
    fetched = local_storage.get_user("testuser")
    assert fetched["first_name"] == "Updated"

def test_local_storage_feedback(local_storage):
    local_storage.save_feedback("testuser", "Great app!", "Test User", "test@example.com")

    with sqlite3.connect(local_storage.db_path) as conn:
        row = conn.execute("SELECT * FROM feedback WHERE username=?", ("testuser",)).fetchone()
        assert row is not None
        assert row[2] == "Test User" # name

def test_local_storage_portfolio(local_storage):
    username = "testuser"
    data = b'{"key": "value"}'

    local_storage.save_portfolio(username, data)
    fetched = local_storage.get_portfolio(username)
    assert fetched == data

    assert local_storage.get_portfolio("unknown") is None

def test_local_storage_journal(local_storage):
    entry = {
        "username": "testuser",
        "symbol": "AAPL",
        "pnl": 100.0,
        "entry_date": "2023-01-01"
    }

    # Insert
    entry_id = local_storage.save_journal_entry(entry)
    assert entry_id is not None

    # Get
    entries = local_storage.get_journal_entries("testuser")
    assert len(entries) == 1
    assert entries[0]["symbol"] == "AAPL"

    # Update
    entry["id"] = entry_id
    entry["pnl"] = 200.0
    local_storage.save_journal_entry(entry)

    entries = local_storage.get_journal_entries("testuser")
    assert len(entries) == 1
    assert entries[0]["pnl"] == 200.0

    # Delete
    local_storage.delete_journal_entry("testuser", entry_id)
    entries = local_storage.get_journal_entries("testuser")
    assert len(entries) == 0

def test_local_storage_migration_trigger(tmp_path):
    # Setup a DB with old schema (missing 'name' in feedback)
    db_path = tmp_path / "old_schema.db"
    with sqlite3.connect(str(db_path)) as conn:
         conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                message TEXT,
                created_at REAL
            )
        """)

    # Initialize LocalStorage, should trigger migration
    storage = LocalStorage(str(db_path))

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("PRAGMA table_info(feedback)")
        columns = [info[1] for info in cursor.fetchall()]
        assert 'name' in columns
        assert 'email' in columns

# --- Tests for PostgresStorage ---

@patch("webapp.storage.create_engine")
@patch("webapp.storage.sessionmaker")
def test_postgres_storage(mock_sessionmaker, mock_create_engine):
    # Setup mocks
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_session = MagicMock()
    mock_sessionmaker.return_value = mock_session
    mock_db_session = MagicMock()
    mock_session.return_value = mock_db_session

    storage = PostgresStorage("postgresql://user:pass@localhost/db")

    # Test save_report
    storage.save_report("token", "file.pdf", b"data")
    assert mock_db_session.merge.called
    assert mock_db_session.commit.called
    assert mock_db_session.close.called

    # Test get_report
    mock_db_session.query.return_value.filter_by.return_value.first.return_value.data = b"data"
    data = storage.get_report("token", "file.pdf")
    assert data == b"data"

    # Test cleanup
    storage.cleanup_old_reports(100)
    assert mock_db_session.query.return_value.filter.return_value.delete.called

    # Test save_user
    storage.save_user({"username": "u"})
    assert mock_db_session.add.called

    # Test get_user
    mock_user = MagicMock()
    mock_user.username = "u"
    # Need to mock __table__.columns for dict comprehension
    # This is tricky with mocks, so we skip exact return value check and just check calls
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = None # Simplest case
    storage.get_user("u")
    assert mock_db_session.query.called

    # Test save_portfolio
    storage.save_portfolio("u", b"{}")
    assert mock_db_session.merge.called

    # Test get_portfolio
    # Setup chain: query -> filter_by -> first -> return an object with .data_json
    mock_portfolio = MagicMock()
    mock_portfolio.data_json = b"{}"
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_portfolio
    res = storage.get_portfolio("u")
    assert res == b"{}"

    # Test journal
    storage.save_journal_entry({"username": "u", "symbol": "A"})
    assert mock_db_session.add.called # New entry

    storage.get_journal_entries("u")
    assert mock_db_session.query.called

    storage.delete_journal_entry("u", "id")
    assert mock_db_session.query.return_value.filter_by.return_value.delete.called

    storage.close()
    assert mock_engine.dispose.called


# --- Tests for get_storage_provider factory ---

def test_get_storage_provider_local(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)

    app = MagicMock()
    app.instance_path = str(tmp_path)

    provider = get_storage_provider(app)
    assert isinstance(provider, LocalStorage)

def test_get_storage_provider_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://...")

    # We don't want to actually connect, so patch PostgresStorage
    with patch("webapp.storage.PostgresStorage") as MockPostgres:
        get_storage_provider(MagicMock())
        assert MockPostgres.called

def test_get_storage_provider_s3(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "fake")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket")

    with patch("webapp.storage.S3Storage") as MockS3:
        get_storage_provider(MagicMock())
        assert MockS3.called

# --- Tests for S3Storage ---
@patch("boto3.client")
def test_s3_storage(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    storage = S3Storage("bucket")

    # Save report
    storage.save_report("t", "f", b"d")
    mock_s3.put_object.assert_called_with(Bucket="bucket", Key="reports/t/f", Body=b"d")

    # Get report
    mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b"d")}
    assert storage.get_report("t", "f") == b"d"

    # Cleanup (complex to test fully, but check paginator call)
    storage.cleanup_old_reports(100)
    mock_s3.get_paginator.assert_called_with('list_objects_v2')

    # Save user
    storage.save_user({"username": "u"})
    mock_s3.put_object.assert_called()

    # Save portfolio
    storage.save_portfolio("u", b"d")
    mock_s3.put_object.assert_called()

    # Get portfolio
    storage.get_portfolio("u")
    mock_s3.get_object.assert_called()

    # Journal
    # Fix the exception class on the mock to allow 'except' to work
    # Boto3 client exceptions are dynamically generated, so usually we just mock the raise
    # But here the code catches `self.s3.exceptions.NoSuchKey`.

    # We need to make sure `storage.s3.exceptions.NoSuchKey` exists and is a class
    type(mock_s3).exceptions = MagicMock()
    # Create a dummy exception class
    class NoSuchKey(Exception): pass
    mock_s3.exceptions.NoSuchKey = NoSuchKey

    # Simulate NoSuchKey when calling get_object
    mock_s3.get_object.side_effect = NoSuchKey("No key")

    storage.save_journal_entry({"username": "u"})
    # Should put object with list
    mock_s3.put_object.assert_called()

import time
