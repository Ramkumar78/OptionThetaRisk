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

def test_registration_flow(client):
    """Test full registration and login flow."""
    # 1. Access protected route without login -> Redirect to /login
    response = client.get('/', follow_redirects=True)
    assert b"Enter your credentials" in response.data
    assert request.path == "/login"

    # 2. Register
    reg_data = {
        "username": "newuser",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "location": "New York",
        "trading_experience": "1-3 Years"
    }
    response = client.post('/register', data=reg_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful" in response.data
    assert request.path == "/login"

    # 3. Login
    login_data = {
        "username": "newuser",
        "password": "password123"
    }
    response = client.post('/login', data=login_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Market Screener" in response.data
    assert request.path == "/"

def test_feedback_flow(client):
    """Test feedback submission."""
    # Register and Login
    client.post('/register', data={"username": "fbuser", "password": "pw", "first_name": "F", "last_name": "B", "location": "L", "trading_experience": "1"}, follow_redirects=True)
    client.post('/login', data={"username": "fbuser", "password": "pw"}, follow_redirects=True)

    # Submit feedback
    response = client.post('/feedback', data={'message': 'Great app!'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Thank you for your feedback!" in response.data

def test_user_capture(client):
    """Test that the user is stored in DB."""
    app = create_app(testing=True)
    with app.app_context():
        db_path = os.path.join(app.instance_path, "reports.db")
        if os.path.exists(db_path):
             os.remove(db_path)

    with app.test_client() as client:
        client.post('/register', data={"username": "dbuser", "password": "pw", "first_name": "D", "last_name": "B", "location": "L", "trading_experience": "1"}, follow_redirects=True)

        # Verify in DB
        with app.app_context():
            from webapp.sqlite_storage import LocalStorage
            storage = get_storage_provider(app)
            assert isinstance(storage, LocalStorage)

            import sqlite3
            with sqlite3.connect(storage.db_path) as conn:
                cursor = conn.execute("SELECT username, first_name FROM users WHERE username = 'dbuser'")
                row = cursor.fetchone()
                assert row is not None
                assert row[0] == 'dbuser'
                assert row[1] == 'D'
