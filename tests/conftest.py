import os
import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture(autouse=True)
def prevent_background_scheduler():
    """Prevent the background scheduler from starting during tests."""
    with patch('webapp.services.scheduler_service.start_scheduler') as mock:
        yield mock

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app(testing=True)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "DATABASE_URL": "sqlite:///:memory:",
    })
    yield app
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(autouse=True)
def prevent_background_scheduler():
    """Prevent the background scheduler from starting during tests."""
    with patch('webapp.services.scheduler_service.start_scheduler') as mock:
        yield mock
