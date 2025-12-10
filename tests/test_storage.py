import os
import pytest
import sqlite3
import uuid
from unittest.mock import MagicMock, patch, ANY
from webapp.storage import DatabaseStorage, S3Storage, get_storage_provider, StorageProvider, Report
from sqlalchemy import create_engine
import time

# --- Tests for DatabaseStorage (Both SQLite and Postgres via SQLAlchemy) ---

@pytest.fixture
def db_storage(tmp_path):
    db_path = tmp_path / "test.db"
    return DatabaseStorage(f"sqlite:///{db_path}")

def test_db_storage_init(db_storage):
    # Check tables exist via SQLAlchemy metadata or raw SQL
    with sqlite3.connect(str(db_storage.engine.url.database)) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        assert "reports" in table_names
        assert "users" in table_names
        assert "feedback" in table_names
        assert "portfolios" in table_names
        assert "journal_entries" in table_names

def test_db_storage_report(db_storage):
    token = "test_token"
    filename = "test.pdf"
    data = b"test content"

    db_storage.save_report(token, filename, data)
    fetched_data = db_storage.get_report(token, filename)
    assert fetched_data == data

    # Non-existent report
    assert db_storage.get_report("bad", "bad") is None

def test_db_storage_cleanup_reports(db_storage):
    token = "test_token"
    filename = "test.pdf"
    data = b"test content"

    # Manually insert with a specific timestamp to avoid mocking time.time() complexity with SQLAlchemy defaults
    session = db_storage.Session()
    # Create a report from 1000 seconds ago (timestamp 1000)
    report = Report(token=token, filename=filename, data=data, created_at=1000.0)
    session.add(report)
    session.commit()
    session.close()

    # Verify exist
    assert db_storage.get_report(token, filename) == data

    # Cleanup with cutoff before 1000.0 (e.g., current time 1100, retention 200 -> cutoff 900)
    # 1000 > 900, so should NOT delete
    with patch("webapp.storage.time.time") as mock_time:
        mock_time.return_value = 1100.0
        db_storage.cleanup_old_reports(200)
    assert db_storage.get_report(token, filename) == data

    # Cleanup with cutoff after 1000.0 (e.g., current time 1100, retention 50 -> cutoff 1050)
    # 1000 < 1050, so SHOULD delete
    with patch("webapp.storage.time.time") as mock_time:
        mock_time.return_value = 1100.0
        db_storage.cleanup_old_reports(50)

    assert db_storage.get_report(token, filename) is None

def test_db_storage_user(db_storage):
    user_data = {
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User"
    }
    db_storage.save_user(user_data)

    fetched = db_storage.get_user("testuser")
    assert fetched["username"] == "testuser"
    assert fetched["first_name"] == "Test"

    # Update
    user_data["first_name"] = "Updated"
    db_storage.save_user(user_data)
    fetched = db_storage.get_user("testuser")
    assert fetched["first_name"] == "Updated"

def test_db_storage_feedback(db_storage):
    db_storage.save_feedback("testuser", "Great app!", "Test User", "test@example.com")

    # We can check directly with SQLAlchemy too
    session = db_storage.Session()
    from webapp.storage import Feedback
    f = session.query(Feedback).filter_by(username="testuser").first()
    assert f is not None
    assert f.name == "Test User"
    session.close()

def test_db_storage_portfolio(db_storage):
    username = "testuser"
    data = b'{"key": "value"}'

    db_storage.save_portfolio(username, data)
    fetched = db_storage.get_portfolio(username)
    assert fetched == data

    assert db_storage.get_portfolio("unknown") is None

def test_db_storage_journal(db_storage):
    entry = {
        "username": "testuser",
        "symbol": "AAPL",
        "pnl": 100.0,
        "entry_date": "2023-01-01"
    }

    # Insert
    entry_id = db_storage.save_journal_entry(entry)
    assert entry_id is not None

    # Get
    entries = db_storage.get_journal_entries("testuser")
    assert len(entries) == 1
    assert entries[0]["symbol"] == "AAPL"

    # Update
    entry["id"] = entry_id
    entry["pnl"] = 200.0
    db_storage.save_journal_entry(entry)

    entries = db_storage.get_journal_entries("testuser")
    assert len(entries) == 1
    assert entries[0]["pnl"] == 200.0

    # Delete
    db_storage.delete_journal_entry("testuser", entry_id)
    entries = db_storage.get_journal_entries("testuser")
    assert len(entries) == 0

# --- Tests for get_storage_provider factory ---

def test_get_storage_provider_local(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)

    app = MagicMock()
    app.instance_path = str(tmp_path)

    provider = get_storage_provider(app)
    assert isinstance(provider, DatabaseStorage)
    assert str(provider.engine.url).startswith("sqlite")

def test_get_storage_provider_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

    # We mock DatabaseStorage to avoid actually connecting
    with patch("webapp.storage.DatabaseStorage") as MockDB:
        get_storage_provider(MagicMock())
        MockDB.assert_called_with("postgresql://user:pass@localhost/db")

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
