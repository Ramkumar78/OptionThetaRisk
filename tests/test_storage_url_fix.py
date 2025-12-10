import os
from unittest.mock import patch, MagicMock
from webapp.storage import get_storage_provider, DatabaseStorage

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
