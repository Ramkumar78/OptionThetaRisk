import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock
from webapp.storage import S3Storage, get_storage_provider, DatabaseStorage
from sqlalchemy import create_engine, text

# --- S3 Storage Tests ---

@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock:
        # We need to setup exceptions on the mock object
        # boto3 clients have an 'exceptions' attribute which holds exception classes
        # We need NoSuchKey to be a real exception class for try/except blocks to work
        exception_class = type("NoSuchKey", (Exception,), {})
        mock.return_value.exceptions.NoSuchKey = exception_class

        yield mock

def test_s3_init(mock_boto3_client):
    storage = S3Storage("my-bucket", "us-east-1")
    assert storage.bucket_name == "my-bucket"
    mock_boto3_client.assert_called_with("s3", region_name="us-east-1")

def test_s3_save_report(mock_boto3_client):
    storage = S3Storage("my-bucket")
    storage.save_report("token", "file.txt", b"data")
    storage.s3.put_object.assert_called_with(
        Bucket="my-bucket", Key="reports/token/file.txt", Body=b"data"
    )

def test_s3_get_report_success(mock_boto3_client):
    storage = S3Storage("my-bucket")
    mock_body = MagicMock()
    mock_body.read.return_value = b"data"
    storage.s3.get_object.return_value = {"Body": mock_body}

    assert storage.get_report("token", "file.txt") == b"data"

def test_s3_get_report_missing(mock_boto3_client):
    storage = S3Storage("my-bucket")
    # Raise the NoSuchKey exception we configured in the fixture
    storage.s3.get_object.side_effect = storage.s3.exceptions.NoSuchKey()

    assert storage.get_report("token", "missing") is None

def test_s3_cleanup_old_reports(mock_boto3_client):
    storage = S3Storage("my-bucket")

    paginator = MagicMock()
    storage.s3.get_paginator.return_value = paginator

    # Old object
    # Mock datetime for list_objects payload

    # We can just rely on mocking the timestamp logic or passing objects
    # Let's mock paginator to return a page with contents
    mock_obj = {"Key": "reports/old", "LastModified": MagicMock()}
    mock_obj["LastModified"].timestamp.return_value = time.time() - 3600 # 1 hour old

    paginator.paginate.return_value = [{"Contents": [mock_obj]}]

    storage.cleanup_old_reports(max_age_seconds=60) # Should delete
    storage.s3.delete_objects.assert_called()

def test_s3_save_user(mock_boto3_client):
    storage = S3Storage("my-bucket")
    storage.save_user({"username": "user", "foo": "bar"})
    storage.s3.put_object.assert_called()

def test_s3_get_user(mock_boto3_client):
    storage = S3Storage("my-bucket")
    mock_body = MagicMock()
    mock_body.read.return_value = b'{"username": "user"}'
    storage.s3.get_object.return_value = {"Body": mock_body}
    assert storage.get_user("user")["username"] == "user"

def test_s3_save_feedback(mock_boto3_client):
    storage = S3Storage("my-bucket")
    storage.save_feedback("user", "msg")
    storage.s3.put_object.assert_called()

def test_s3_portfolio(mock_boto3_client):
    storage = S3Storage("my-bucket")
    storage.save_portfolio("user", b"json")
    storage.s3.put_object.assert_called()

    mock_body = MagicMock()
    mock_body.read.return_value = b"json"
    storage.s3.get_object.return_value = {"Body": mock_body}
    assert storage.get_portfolio("user") == b"json"

def test_s3_journal_workflow(mock_boto3_client):
    storage = S3Storage("my-bucket")

    # Initial get returns NoSuchKey
    storage.s3.get_object.side_effect = storage.s3.exceptions.NoSuchKey()

    # Save
    entry = {"username": "user", "symbol": "AAPL"}
    eid = storage.save_journal_entry(entry)
    assert eid
    assert storage.s3.put_object.called

    # Get with data
    storage.s3.get_object.side_effect = None
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps([entry]).encode('utf-8')
    storage.s3.get_object.return_value = {"Body": mock_body}

    entries = storage.get_journal_entries("user")
    assert len(entries) == 1

    # Delete
    storage.delete_journal_entry("user", eid)
    assert storage.s3.put_object.call_count >= 2 # Initial save + delete save

# --- Get Storage Provider Logic ---

def test_get_storage_provider_postgres():
    app = MagicMock()
    with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@host/db"}):
        with patch("webapp.storage.DatabaseStorage") as mock_db:
            get_storage_provider(app)
            # Check string replacement
            mock_db.assert_called_with("postgresql://user:pass@host/db")

def test_get_storage_provider_s3():
    app = MagicMock()
    with patch.dict(os.environ, {"DATABASE_URL": "", "AWS_ACCESS_KEY_ID": "key", "S3_BUCKET_NAME": "bucket"}):
        with patch("webapp.storage.S3Storage") as mock_s3:
            get_storage_provider(app)
            mock_s3.assert_called_with(bucket_name="bucket", region_name="us-east-1")

def test_get_storage_provider_sqlite():
    app = MagicMock()
    app.instance_path = "/tmp"
    with patch.dict(os.environ, {}, clear=True):
        # Ensure AWS/DB env vars are missing
        with patch("webapp.storage.DatabaseStorage") as mock_db:
            get_storage_provider(app)
            mock_db.assert_called_with("sqlite:////tmp/reports.db")

# --- Database Schema Migration Coverage ---

from sqlalchemy import inspect
from webapp.storage import DatabaseStorage

@pytest.fixture
def sqlite_storage():
    # Use in-memory sqlite
    storage = DatabaseStorage("sqlite:///:memory:")
    yield storage
    storage.close()

def test_schema_migration_logic(tmp_path):
    # We want to test the _ensure_schema_migrations logic.
    # Use tmp_path for the DB file to avoid "PermissionError" on cleanup.
    db_file = tmp_path / "test_migration.db"
    
    url = f"sqlite:///{str(db_file)}"
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
             # Create incomplete table
             conn.execute(text("CREATE TABLE journal_entries (id TEXT PRIMARY KEY, username TEXT)"))
             conn.commit()
    finally:
        engine.dispose()

    # Now init Storage, which should migrate
    storage = DatabaseStorage(url)

    try:
        # Verify columns exist
        insp = inspect(storage.engine)
        cols = [c['name'] for c in insp.get_columns('journal_entries')]
        assert 'entry_date' in cols
        assert 'entry_time' in cols
        assert 'sentiment' in cols
    
    finally:
        storage.close()

# --- Imports for types ---
from datetime import datetime, timedelta
