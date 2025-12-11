import pytest
import os
import json
import time
import uuid
from unittest.mock import MagicMock, patch, ANY
from sqlalchemy import create_engine, inspect, text
from webapp.storage import DatabaseStorage, S3Storage, get_storage_provider, JournalEntry, User

# --- Fixtures ---

@pytest.fixture
def sqlite_storage(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    storage = DatabaseStorage(db_url)
    yield storage
    storage.close()

@pytest.fixture
def mock_s3_storage():
    with patch('boto3.client') as mock_boto:
        storage = S3Storage(bucket_name="test-bucket", region_name="us-east-1")
        # Fix for ClientError/NoSuchKey being a mock
        class MockClientError(Exception):
            pass
        class MockNoSuchKey(Exception):
            pass

        # Configure exceptions on the mock client
        storage.s3.exceptions.ClientError = MockClientError
        storage.s3.exceptions.NoSuchKey = MockNoSuchKey

        yield storage, mock_boto

# --- DatabaseStorage Tests ---

def test_db_save_and_get_report(sqlite_storage):
    token = "token123"
    filename = "report.pdf"
    data = b"pdf_data"

    sqlite_storage.save_report(token, filename, data)
    retrieved = sqlite_storage.get_report(token, filename)
    assert retrieved == data

    assert sqlite_storage.get_report("bad", "token") is None

def test_db_cleanup_reports(sqlite_storage):
    token = "token123"
    filename = "report.pdf"
    data = b"pdf_data"

    sqlite_storage.save_report(token, filename, data)

    # Manually update created_at to be old
    session = sqlite_storage.Session()
    session.execute(text("UPDATE reports SET created_at = :t"), {'t': time.time() - 2000})
    session.commit()
    session.close()

    sqlite_storage.cleanup_old_reports(1000)
    assert sqlite_storage.get_report(token, filename) is None

def test_db_user_operations(sqlite_storage):
    user_data = {"username": "user1", "first_name": "Test"}
    sqlite_storage.save_user(user_data)

    retrieved = sqlite_storage.get_user("user1")
    assert retrieved['first_name'] == "Test"

    # Update
    user_data['last_name'] = "User"
    sqlite_storage.save_user(user_data)
    retrieved = sqlite_storage.get_user("user1")
    assert retrieved['last_name'] == "User"
    assert retrieved['first_name'] == "Test" # Should persist

def test_db_feedback(sqlite_storage):
    sqlite_storage.save_feedback("user1", "msg")
    # No get method for feedback in interface, but check DB
    session = sqlite_storage.Session()
    from webapp.storage import Feedback
    f = session.query(Feedback).first()
    assert f.username == "user1"
    assert f.message == "msg"
    session.close()

def test_db_portfolio(sqlite_storage):
    data = b'{"a": 1}'
    sqlite_storage.save_portfolio("user1", data)
    assert sqlite_storage.get_portfolio("user1") == data

def test_db_journal_crud(sqlite_storage):
    entry = {
        "username": "user1",
        "symbol": "AAPL",
        "pnl": 100.0
    }
    eid = sqlite_storage.save_journal_entry(entry)
    assert eid

    entries = sqlite_storage.get_journal_entries("user1")
    assert len(entries) == 1
    assert entries[0]['symbol'] == "AAPL"

    # Update
    entry['id'] = eid
    entry['pnl'] = 200.0
    sqlite_storage.save_journal_entry(entry)
    entries = sqlite_storage.get_journal_entries("user1")
    assert entries[0]['pnl'] == 200.0

    # Delete
    sqlite_storage.delete_journal_entry("user1", eid)
    assert len(sqlite_storage.get_journal_entries("user1")) == 0

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

# --- S3Storage Tests ---

def test_s3_save_get_report(mock_s3_storage):
    storage, mock_boto = mock_s3_storage
    mock_s3 = mock_boto.return_value

    storage.save_report("token", "file", b"data")
    mock_s3.put_object.assert_called()

    mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b"data")}
    assert storage.get_report("token", "file") == b"data"

    # Exception handling
    mock_s3.get_object.side_effect = storage.s3.exceptions.NoSuchKey()
    assert storage.get_report("token", "file") is None

def test_s3_cleanup(mock_s3_storage):
    storage, mock_boto = mock_s3_storage
    mock_s3 = mock_boto.return_value

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

def test_s3_user_ops(mock_s3_storage):
    storage, mock_boto = mock_s3_storage
    mock_s3 = mock_boto.return_value

    storage.save_user({"username": "u1"})
    mock_s3.put_object.assert_called()

    mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b'{"username": "u1"}')}
    assert storage.get_user("u1")['username'] == "u1"

def test_s3_journal_ops(mock_s3_storage):
    storage, mock_boto = mock_s3_storage
    mock_s3 = mock_boto.return_value

    # Initial empty get
    mock_s3.get_object.side_effect = storage.s3.exceptions.NoSuchKey()

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

# --- Helper Tests ---

def test_get_storage_provider(tmp_path):
    app = MagicMock()
    app.instance_path = str(tmp_path)

    # Default SQLite
    with patch.dict(os.environ, {}, clear=True):
        s = get_storage_provider(app)
        assert isinstance(s, DatabaseStorage)
        assert s.is_sqlite
        s.close()

    # Postgres - Mock DatabaseStorage to avoid connection
    with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@host/db"}):
        with patch('webapp.storage.DatabaseStorage') as mock_db:
            s = get_storage_provider(app)
            # Check URL replacement
            args, _ = mock_db.call_args
            assert args[0] == "postgresql://user:pass@host/db"

    # S3
    with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "key", "S3_BUCKET_NAME": "bucket"}, clear=True):
        with patch('webapp.storage.S3Storage') as mock_s3:
            s = get_storage_provider(app)
            assert mock_s3.called
