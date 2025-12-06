import pytest
from flask import request
from webapp.app import create_app
from webapp.storage import get_storage_provider
import os

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_login_flow(client):
    """Test that login redirects to index and stores user email."""
    # 1. Access protected route without login -> Redirect to /login
    response = client.get('/', follow_redirects=True)
    assert b"Enter your email to access the platform" in response.data
    assert request.path == "/login"

    # 2. Perform Login
    response = client.post('/login', data={'email': 'test@example.com'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Market Screener" in response.data # Should be on index/upload page

    # 3. Check Session (implicitly via access) and Storage
    # We can inspect the DB directly or verify access to protected route
    response = client.get('/')
    assert response.status_code == 200 # Access granted

def test_feedback_flow(client):
    """Test feedback submission."""
    # Login first
    client.post('/login', data={'email': 'test@example.com'})

    # Submit feedback
    response = client.post('/feedback', data={'message': 'Great app!'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Thank you for your feedback!" in response.data

def test_email_capture(client):
    """Test that the user email is actually stored in the DB."""
    app = create_app(testing=True)
    with app.app_context():
        # Clean DB
        db_path = os.path.join(app.instance_path, "reports.db")
        if os.path.exists(db_path):
             os.remove(db_path)

    with app.test_client() as client:
        client.post('/login', data={'email': 'stored@example.com'})

        # Verify in DB
        with app.app_context():
            from webapp.sqlite_storage import LocalStorage
            storage = get_storage_provider(app)
            assert isinstance(storage, LocalStorage)

            import sqlite3
            with sqlite3.connect(storage.db_path) as conn:
                cursor = conn.execute("SELECT email FROM users WHERE email = 'stored@example.com'")
                row = cursor.fetchone()
                assert row is not None
                assert row[0] == 'stored@example.com'
