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
    app = create_app(testing=True)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "DATABASE_URL": "sqlite:///:memory:",
    })
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def authed_client(client):
    """A test client that is pre-authenticated."""
    with client.session_transaction() as session:
        session['username'] = 'testuser'
    return client
