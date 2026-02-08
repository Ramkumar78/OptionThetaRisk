import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from flask import Flask, g, jsonify
from pydantic import BaseModel
from webapp.utils import _get_env_or_docker_default, send_email_notification
from webapp.validation import validate_schema

# --- Tests for _get_env_or_docker_default ---

def test_get_env_or_docker_default_env_var_set():
    """Test that environment variable takes precedence."""
    with patch.dict(os.environ, {"TEST_KEY": "env_value"}):
        assert _get_env_or_docker_default("TEST_KEY", "default") == "env_value"

def test_get_env_or_docker_default_docker_compose_exists():
    """Test fallback to docker-compose.yml default value."""
    docker_content = """
    services:
      web:
        environment:
          - TEST_KEY=${TEST_KEY:-docker_value}
    """
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=docker_content)):
                assert _get_env_or_docker_default("TEST_KEY", "default") == "docker_value"

def test_get_env_or_docker_default_docker_compose_no_key():
    """Test fallback to default when key is missing in docker-compose.yml."""
    docker_content = "some content without the key"
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=docker_content)):
                assert _get_env_or_docker_default("TEST_KEY", "default") == "default"

def test_get_env_or_docker_default_no_docker_compose():
    """Test fallback to default when docker-compose.yml does not exist."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=False):
            assert _get_env_or_docker_default("TEST_KEY", "default") == "default"


# --- Tests for send_email_notification ---

@patch("webapp.utils._get_env_or_docker_default")
@patch("webapp.utils.resend")
def test_send_email_notification_no_api_key(mock_resend, mock_get_env):
    """Test that email is skipped if API key is missing."""
    mock_get_env.return_value = None

    send_email_notification("Subject", "Body")

    mock_resend.Emails.send.assert_not_called()

@patch("webapp.utils._get_env_or_docker_default")
@patch("webapp.utils.resend")
def test_send_email_notification_success(mock_resend, mock_get_env):
    """Test that email is sent if API key is present."""
    mock_get_env.return_value = "fake_api_key"
    mock_resend.Emails.send.return_value = {"id": "12345"}

    send_email_notification("Subject", "Body")

    assert mock_resend.api_key == "fake_api_key"
    mock_resend.Emails.send.assert_called_once()
    args, kwargs = mock_resend.Emails.send.call_args
    assert kwargs == {} # it's called with a dictionary as first arg
    params = args[0]
    assert params["to"] == ["shriram2222@gmail.com"]
    assert params["subject"] == "Subject"
    assert params["text"] == "Body"


# --- Tests for validate_schema ---

class MockModel(BaseModel):
    name: str
    age: int

def test_validate_schema_valid_json():
    """Test that valid JSON is stored in g.validated_data."""
    app = Flask(__name__)

    @app.route("/test", methods=["POST"])
    @validate_schema(MockModel)
    def test_route():
        return jsonify({"message": "success", "data": g.validated_data.model_dump()})

    with app.test_request_context(path="/test", method="POST", json={"name": "Alice", "age": 30}):
        # Call the decorated function directly since we are in a request context
        response = test_route()

        # Depending on implementation, it might return a Response object or tuple or whatever the route returns
        # Here route returns jsonify response
        # Note: In a real request, Flask converts the return value to a Response object.
        # But calling the function directly returns what the function returns.
        # test_route returns a Response object (from jsonify).

        assert response.status_code == 200
        assert g.validated_data.name == "Alice"
        assert g.validated_data.age == 30

def test_validate_schema_invalid_json():
    """Test that invalid JSON returns 400."""
    app = Flask(__name__)

    @app.route("/test", methods=["POST"])
    @validate_schema(MockModel)
    def test_route():
        return "Should not reach here"

    with app.test_request_context(path="/test", method="POST", json={"name": "Alice", "age": "not an int"}):
        # The decorator catches exception and returns (jsonify(...), 400)
        response, status_code = test_route()

        assert status_code == 400
        assert response.json["error"] == "Validation Error"
        # Check details
        details = response.json["details"]
        assert any(d["field"] == "age" for d in details)

def test_validate_schema_missing_field():
    """Test that missing required field returns 400."""
    app = Flask(__name__)

    @app.route("/test", methods=["POST"])
    @validate_schema(MockModel)
    def test_route():
        return "Should not reach here"

    with app.test_request_context(path="/test", method="POST", json={"name": "Alice"}):
        response, status_code = test_route()

        assert status_code == 400
        assert response.json["error"] == "Validation Error"
        details = response.json["details"]
        assert any(d["field"] == "age" for d in details)
