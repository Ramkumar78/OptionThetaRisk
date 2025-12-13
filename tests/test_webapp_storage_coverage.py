import unittest
from unittest.mock import MagicMock, patch, ANY
from sqlalchemy.exc import SQLAlchemyError
from webapp.storage import DatabaseStorage, S3Storage, JournalEntry, User, Report, Feedback, Portfolio
import uuid

class TestDatabaseStorageCoverage(unittest.TestCase):
    def setUp(self):
        self.db_url = "sqlite:///:memory:"
        # Clear cache to force new engine
        DatabaseStorage._engines = {}
        self.storage = DatabaseStorage(self.db_url)

    def tearDown(self):
        self.storage.close()

    def test_ensure_schema_migrations_mocked(self):
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

    def test_ensure_schema_migrations_exception(self):
         with patch('webapp.storage.inspect') as mock_inspect:
             mock_inspect.side_effect = Exception("Migration Failed")
             # Should print error but not crash
             DatabaseStorage._ensure_schema_migrations(self.storage.engine)

    def test_save_user_update(self):
        # Test update existing user logic
        user_data = {"username": "testuser", "first_name": "Test"}
        self.storage.save_user(user_data)

        # Update
        update_data = {"username": "testuser", "first_name": "Updated"}
        self.storage.save_user(update_data)

        user = self.storage.get_user("testuser")
        assert user['first_name'] == "Updated"

    def test_save_journal_entry_sanitization(self):
        # Test that extra keys are ignored
        entry = {
            "username": "user1",
            "entry_date": "2023-01-01",
            "invalid_column": "should_be_ignored"
        }
        eid = self.storage.save_journal_entry(entry)

        saved = self.storage.get_journal_entries("user1")[0]
        assert saved['id'] == eid
        # Ideally we check that no error occurred during save due to invalid key

    def test_save_journal_entries_batch_update(self):
        # Insert one
        e1 = {"username": "u1", "symbol": "AAPL", "qty": 10}
        self.storage.save_journal_entries([e1])
        saved = self.storage.get_journal_entries("u1")[0]
        eid = saved['id']

        # Update it via batch
        e1_update = {"id": eid, "username": "u1", "symbol": "AAPL", "qty": 20}
        count = self.storage.save_journal_entries([e1_update])
        assert count == 1

        updated = self.storage.get_journal_entries("u1")[0]
        assert updated['qty'] == 20.0

    def test_get_user_none(self):
        assert self.storage.get_user("nonexistent") is None

    def test_get_report_none(self):
        assert self.storage.get_report("badtoken", "badfile") is None

    def test_cleanup_vacuum_sqlite(self):
        # Test vacuum execution for sqlite
        # We need to ensure cleanup_old_reports calls execute("VACUUM")

        # Patch the Session used inside cleanup_old_reports
        with patch.object(self.storage, 'Session') as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            self.storage.cleanup_old_reports(0)

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

class TestS3StorageCoverage(unittest.TestCase):
    def setUp(self):
        self.storage = S3Storage("test-bucket", "us-east-1")
        self.storage.s3 = MagicMock()
        # Ensure exceptions class exists on mock
        self.storage.s3.exceptions.NoSuchKey = Exception

    def test_get_report_exception(self):
        self.storage.s3.get_object.side_effect = Exception("S3 Error")
        assert self.storage.get_report("t", "f") is None

    def test_cleanup_old_reports_exception(self):
        self.storage.s3.get_paginator.side_effect = Exception("S3 Error")
        # Should catch and pass
        self.storage.cleanup_old_reports(100)

    def test_save_user_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        self.storage.save_user({"username": "u"})

    def test_get_user_exception(self):
        self.storage.s3.get_object.side_effect = Exception("S3 Error")
        assert self.storage.get_user("u") is None

    def test_save_feedback_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        self.storage.save_feedback("u", "msg")

    def test_save_portfolio_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        self.storage.save_portfolio("u", b"data")

    def test_get_portfolio_exception(self):
        self.storage.s3.get_object.side_effect = Exception("S3 Error")
        assert self.storage.get_portfolio("u") is None

    def test_save_journal_entry_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        assert self.storage.save_journal_entry({"username": "u"}) is None

    def test_save_journal_entries_batch_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        count = self.storage.save_journal_entries([{"username": "u"}])
        assert count == 0

    def test_delete_journal_entry_exception(self):
        self.storage.s3.put_object.side_effect = Exception("S3 Error")
        self.storage.delete_journal_entry("u", "id")
