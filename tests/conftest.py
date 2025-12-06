import pytest
from webapp.app import create_app

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
    """A test client for the app (unauthenticated)."""
    return app.test_client()

@pytest.fixture
def authed_client(client):
    """A test client with a user logged in."""
    with client.session_transaction() as sess:
        sess['username'] = "testuser"
    return client
