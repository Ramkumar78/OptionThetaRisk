import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from flask import Flask, jsonify, g
from pydantic import BaseModel
from webapp.utils import _get_env_or_docker_default, handle_api_error
from webapp.validation import validate_schema

# --- Test Data & Models ---

class SampleModel(BaseModel):
    name: str
    age: int
    active: bool = True

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

# --- Tests for _get_env_or_docker_default ---

def test_get_env_var_priority():
    """Test that environment variable takes precedence over docker-compose and default."""
    with patch.dict(os.environ, {"TEST_KEY": "env_val"}):
        assert _get_env_or_docker_default("TEST_KEY", "default") == "env_val"

def test_get_docker_compose_fallback():
    """Test fallback to docker-compose.yml default value when env var is missing."""
    docker_content = """
    services:
      web:
        environment:
          - TEST_KEY=${TEST_KEY:-docker_val}
    """
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=docker_content)):
                assert _get_env_or_docker_default("TEST_KEY", "default") == "docker_val"

def test_get_default_fallback():
    """Test fallback to provided default when key is missing in env and docker-compose."""
    docker_content = "some other content"
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=docker_content)):
                assert _get_env_or_docker_default("TEST_KEY", "default_val") == "default_val"

def test_get_docker_file_missing():
    """Test fallback to default when docker-compose.yml does not exist."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=False):
            assert _get_env_or_docker_default("TEST_KEY", "default_val") == "default_val"


# --- Tests for handle_api_error ---

def test_handle_api_error_returns_500(app, client):
    """Test that handle_api_error catches exceptions and returns 500 JSON."""

    @app.route("/error")
    @handle_api_error
    def error_route():
        raise ValueError("Something went wrong")

    # Mock logger to verify logging
    app.logger = MagicMock()

    response = client.get("/error")

    assert response.status_code == 500
    assert response.is_json
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Something went wrong"

    # Verify logging
    app.logger.exception.assert_called_once()
    args, _ = app.logger.exception.call_args
    assert "API Error in error_route: Something went wrong" in args[0]


# --- Tests for validate_schema ---

def test_validate_schema_valid_payload(app, client):
    """Test validate_schema with a valid JSON payload."""

    @app.route("/validate", methods=["POST"])
    @validate_schema(SampleModel)
    def validate_route():
        return jsonify(g.validated_data.model_dump())

    payload = {"name": "Alice", "age": 30}
    response = client.post("/validate", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Alice"
    assert data["age"] == 30
    assert data["active"] is True  # Default value

def test_validate_schema_invalid_type(app, client):
    """Test validate_schema with invalid field type returns 400."""

    @app.route("/validate", methods=["POST"])
    @validate_schema(SampleModel)
    def validate_route():
        return jsonify({"status": "ok"})

    payload = {"name": "Bob", "age": "not-an-int"}
    response = client.post("/validate", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation Error"
    assert any(d["field"] == "age" for d in data["details"])

def test_validate_schema_missing_field(app, client):
    """Test validate_schema with missing required field returns 400."""

    @app.route("/validate", methods=["POST"])
    @validate_schema(SampleModel)
    def validate_route():
        return jsonify({"status": "ok"})

    payload = {"name": "Charlie"} # Missing age
    response = client.post("/validate", json=payload)

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation Error"
    assert any(d["field"] == "age" for d in data["details"])

def test_validate_schema_empty_payload(app, client):
    """Test validate_schema with empty/None payload (fails validation if fields required)."""

    @app.route("/validate", methods=["POST"])
    @validate_schema(SampleModel)
    def validate_route():
        return jsonify({"status": "ok"})

    # Sending empty body which results in None for get_json() usually,
    # but wrapper handles None -> {}
    # {} fails validation because 'name' and 'age' are required.
    response = client.post("/validate", data=None, content_type="application/json")

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation Error"
