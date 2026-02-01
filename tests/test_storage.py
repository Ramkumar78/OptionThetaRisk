import os
import pytest
import sqlite3
import uuid
import json
from unittest.mock import MagicMock, patch, ANY
from webapp.storage import DatabaseStorage, S3Storage, get_storage_provider, Report
from sqlalchemy import create_engine, inspect, text
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

def test_db_schema_migration(tmp_path):
    # Create DB with missing columns manually first
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)

    # Create table manually without new columns
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE journal_entries (id VARCHAR PRIMARY KEY, username VARCHAR, symbol VARCHAR)"))
        conn.commit()

    # Initialize storage, should trigger migration
    storage = DatabaseStorage(db_url)

    # Check if columns added
    insp = inspect(storage.engine)
    cols = [c['name'] for c in insp.get_columns('journal_entries')]
    assert 'entry_date' in cols
    assert 'entry_time' in cols
    assert 'sentiment' in cols

    storage.close()

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

@patch("boto3.client")
def test_s3_cleanup_detailed(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    storage = S3Storage("bucket")

    # Mock list objects
    mock_paginator = MagicMock()
    mock_s3.get_paginator.return_value = mock_paginator

    old_time = time.time() - 2000

    # Mock datetime for timestamp()
    mock_obj = {'Key': 'old_file', 'LastModified': MagicMock()}
    mock_obj['LastModified'].timestamp.return_value = old_time

    mock_paginator.paginate.return_value = [{'Contents': [mock_obj]}]

    storage.cleanup_old_reports(1000)
    mock_s3.delete_objects.assert_called()

@patch("boto3.client")
def test_s3_journal_ops_detailed(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    storage = S3Storage("bucket")

    # Setup exceptions
    type(mock_s3).exceptions = MagicMock()
    class NoSuchKey(Exception): pass
    mock_s3.exceptions.NoSuchKey = NoSuchKey

    # Initial empty get
    mock_s3.get_object.side_effect = NoSuchKey("No key")

    entry = {"username": "u1", "symbol": "AAPL"}
    eid = storage.save_journal_entry(entry)
    assert eid
    mock_s3.put_object.assert_called()

    # Mock getting entries
    mock_s3.get_object.side_effect = None
    mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: json.dumps([entry]).encode())}

    entries = storage.get_journal_entries("u1")
    assert len(entries) == 1

    # Delete
    storage.delete_journal_entry("u1", eid)
    mock_s3.put_object.assert_called()

# --- Fix Tests ---

def test_get_storage_provider_postgres_fix(monkeypatch):
    # Simulate a provider giving postgres://
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")

    with patch("webapp.storage.DatabaseStorage") as MockDB:
        get_storage_provider(MagicMock())
        # Should be converted to postgresql://
        MockDB.assert_called_with("postgresql://user:pass@host/db")

def test_get_storage_provider_postgresql_ok(monkeypatch):
    # Already correct
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")

    with patch("webapp.storage.DatabaseStorage") as MockDB:
        get_storage_provider(MagicMock())
        MockDB.assert_called_with("postgresql://user:pass@host/db")

# --- Migrated and Refactored from test_webapp_storage_coverage.py ---

@pytest.fixture
def coverage_db_storage():
    db_url = "sqlite:///:memory:"
    # Clear cache to force new engine
    DatabaseStorage._engines = {}
    storage = DatabaseStorage(db_url)
    yield storage
    storage.close()

def test_ensure_schema_migrations_mocked():
    # We need to patch where `inspect` is imported in `webapp.storage`
    with patch('webapp.storage.inspect') as mock_inspect:
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.has_table.return_value = True
        mock_inspector.get_columns.return_value = [{'name': 'id'}]

        # We need a mock engine that returns a mock connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        DatabaseStorage._ensure_schema_migrations(mock_engine)

        assert mock_conn.execute.call_count >= 3

def test_ensure_schema_migrations_exception(coverage_db_storage):
        with patch('webapp.storage.inspect') as mock_inspect:
            mock_inspect.side_effect = Exception("Migration Failed")
            # Should print error but not crash
            DatabaseStorage._ensure_schema_migrations(coverage_db_storage.engine)

def test_save_user_update(coverage_db_storage):
    # Test update existing user logic
    user_data = {"username": "testuser", "first_name": "Test"}
    coverage_db_storage.save_user(user_data)

    # Update
    update_data = {"username": "testuser", "first_name": "Updated"}
    coverage_db_storage.save_user(update_data)

    user = coverage_db_storage.get_user("testuser")
    assert user['first_name'] == "Updated"

def test_save_journal_entry_sanitization(coverage_db_storage):
    # Test that extra keys are ignored
    entry = {
        "username": "user1",
        "entry_date": "2023-01-01",
        "invalid_column": "should_be_ignored"
    }
    eid = coverage_db_storage.save_journal_entry(entry)

    saved = coverage_db_storage.get_journal_entries("user1")[0]
    assert saved['id'] == eid
    # Ideally we check that no error occurred during save due to invalid key

def test_save_journal_entries_batch_update(coverage_db_storage):
    # Insert one
    e1 = {"username": "u1", "symbol": "AAPL", "qty": 10}
    coverage_db_storage.save_journal_entries([e1])
    saved = coverage_db_storage.get_journal_entries("u1")[0]
    eid = saved['id']

    # Update it via batch
    e1_update = {"id": eid, "username": "u1", "symbol": "AAPL", "qty": 20}
    count = coverage_db_storage.save_journal_entries([e1_update])
    assert count == 1

    updated = coverage_db_storage.get_journal_entries("u1")[0]
    assert updated['qty'] == 20.0

def test_get_user_none(coverage_db_storage):
    assert coverage_db_storage.get_user("nonexistent") is None

def test_get_report_none(coverage_db_storage):
    assert coverage_db_storage.get_report("badtoken", "badfile") is None

def test_cleanup_vacuum_sqlite(coverage_db_storage):
    # Test vacuum execution for sqlite
    # We need to ensure cleanup_old_reports calls execute("VACUUM")

    # Patch the Session used inside cleanup_old_reports
    with patch.object(coverage_db_storage, 'Session') as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        coverage_db_storage.cleanup_old_reports(0)

        # Check for VACUUM call
        # It calls session.execute(text("VACUUM"))
        # We check if execute was called with something containing "VACUUM"
        found = False
        for call in mock_session.execute.call_args_list:
            arg = call[0][0]
            if "VACUUM" in str(arg):
                found = True
                break
        assert found

@pytest.fixture
def coverage_s3_storage():
    storage = S3Storage("test-bucket", "us-east-1")
    storage.s3 = MagicMock()
    # Ensure exceptions class exists on mock
    storage.s3.exceptions.NoSuchKey = Exception
    return storage

def test_get_report_exception(coverage_s3_storage):
    coverage_s3_storage.s3.get_object.side_effect = Exception("S3 Error")
    assert coverage_s3_storage.get_report("t", "f") is None

def test_cleanup_old_reports_exception(coverage_s3_storage):
    coverage_s3_storage.s3.get_paginator.side_effect = Exception("S3 Error")
    # Should catch and pass
    coverage_s3_storage.cleanup_old_reports(100)

def test_save_user_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    coverage_s3_storage.save_user({"username": "u"})

def test_get_user_exception(coverage_s3_storage):
    coverage_s3_storage.s3.get_object.side_effect = Exception("S3 Error")
    assert coverage_s3_storage.get_user("u") is None

def test_save_feedback_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    coverage_s3_storage.save_feedback("u", "msg")

def test_save_portfolio_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    coverage_s3_storage.save_portfolio("u", b"data")

def test_get_portfolio_exception(coverage_s3_storage):
    coverage_s3_storage.s3.get_object.side_effect = Exception("S3 Error")
    assert coverage_s3_storage.get_portfolio("u") is None

def test_save_journal_entry_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    assert coverage_s3_storage.save_journal_entry({"username": "u"}) is None

def test_save_journal_entries_batch_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    count = coverage_s3_storage.save_journal_entries([{"username": "u"}])
    assert count == 0

def test_delete_journal_entry_exception(coverage_s3_storage):
    coverage_s3_storage.s3.put_object.side_effect = Exception("S3 Error")
    coverage_s3_storage.delete_journal_entry("u", "id")
