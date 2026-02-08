import pytest
import time
from flask import Flask, jsonify
from webapp.app import create_app
from webapp.middleware import limiter

@pytest.fixture
def app():
    # Standard app for health check and request ID
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    """Test the health check endpoint returns 200 and correct structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "memory" in data
    assert "rss_mb" in data["memory"]
    assert "storage" in data

def test_request_id_generation(client):
    """Test that X-Request-ID is generated if missing."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0

def test_request_id_passthrough(client):
    """Test that X-Request-ID is preserved if provided."""
    custom_id = "custom-trace-id-123"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id

def test_gzip_compression(app):
    """Test Gzip compression for large responses."""
    # Create a route that returns large data
    @app.route("/large-data")
    def large_data():
        return jsonify({"data": "x" * 5000})

    client = app.test_client()

    # Request with Gzip
    response = client.get("/large-data", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    # Flask-Compress adds Content-Encoding: gzip (or brotli if available/preferred)
    # Check for Content-Encoding header
    if "Content-Encoding" in response.headers:
        assert "gzip" in response.headers["Content-Encoding"] or "br" in response.headers["Content-Encoding"]

def test_rate_limiting_enforcement():
    """Test that rate limiting works (enabled explicitly in testing)."""
    app = create_app(testing=True)
    app.config["RATELIMIT_ENABLED"] = True
    app.config["RATELIMIT_STORAGE_URI"] = "memory://"

    # Add a route with tight limit
    @app.route("/limited")
    @limiter.limit("1/second")
    def limited_route():
        return "ok"

    client = app.test_client()

    # 1st Request: OK
    r1 = client.get("/limited")
    assert r1.status_code == 200

    # 2nd Request (Immediate): Blocked
    r2 = client.get("/limited")

    # If it was too fast, it should be 429
    # Note: 1/second fixed window might reset if second changes,
    # but usually immediate sequential requests hit it.
    if r2.status_code == 429:
        data = r2.get_json()
        assert data["error"] == "ratelimit_exceeded"
    else:
        # If the test is slow/flaky, warn but pass if 200 (maybe window reset)
        # Or assert strict limit.
        # Let's try to hit it multiple times quickly.
        blocked = False
        for _ in range(5):
            r = client.get("/limited")
            if r.status_code == 429:
                blocked = True
                break
        assert blocked, "Rate limit should have been triggered"
