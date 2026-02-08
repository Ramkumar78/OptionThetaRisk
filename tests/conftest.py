import os
import pytest
from unittest.mock import patch
from webapp.app import create_app

class SynchronousPool:
    """Mock for multiprocessing.Pool that runs tasks synchronously."""
    def __init__(self, processes=None):
        pass

    def apply_async(self, func, args=(), kwds=None, callback=None, error_callback=None):
        if kwds is None:
            kwds = {}
        try:
            func(*args, **kwds)
        except Exception as e:
            if error_callback:
                error_callback(e)
            else:
                print(f"SyncPool Error: {e}")
        return None

    def close(self):
        pass

    def join(self):
        pass

@pytest.fixture(autouse=True)
def mock_multiprocessing_pool():
    """Mock multiprocessing.Pool to run tasks synchronously during tests."""
    with patch("multiprocessing.Pool", side_effect=SynchronousPool) as mock:
        yield mock

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
