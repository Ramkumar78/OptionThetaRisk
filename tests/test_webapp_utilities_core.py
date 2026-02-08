import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
from flask import Flask
from webapp.utils import _allowed_filename, _get_env_or_docker_default, handle_api_error

class TestWebappUtilitiesCore(unittest.TestCase):

    def test_allowed_filename(self):
        # Case 1: Valid CSV extensions (case-insensitive)
        self.assertTrue(_allowed_filename("data.csv"))
        self.assertTrue(_allowed_filename("DATA.CSV"))
        self.assertTrue(_allowed_filename("Mixed.Csv"))

        # Case 2: Invalid extensions
        self.assertFalse(_allowed_filename("data.txt"))
        self.assertFalse(_allowed_filename("image.png"))
        self.assertFalse(_allowed_filename("script.py"))
        self.assertFalse(_allowed_filename("archive.zip"))

        # Case 3: No extension or hidden files
        self.assertFalse(_allowed_filename("data"))
        self.assertFalse(_allowed_filename(".gitignore"))

        # Case 4: Path traversal attempts (should just check extension)
        self.assertTrue(_allowed_filename("../../etc/passwd.csv"))
        self.assertFalse(_allowed_filename("../../etc/passwd"))

    @patch.dict(os.environ, {}, clear=True)
    def test_get_env_or_docker_default_regex(self):
        # Mock docker-compose.yml content
        # The regex expects: key=${key:-default}
        docker_compose_content = """
        version: '3.8'
        services:
          web:
            environment:
              - DATABASE_URL=${DATABASE_URL:-postgres://user:pass@db:5432/db}
              - SECRET_KEY=${SECRET_KEY:-supersecret}
              - DEBUG=${DEBUG:-True}
        """

        with patch("builtins.open", mock_open(read_data=docker_compose_content)):
            with patch("os.path.exists", return_value=True):
                # Test extraction of existing keys in docker-compose
                self.assertEqual(_get_env_or_docker_default("DATABASE_URL"), "postgres://user:pass@db:5432/db")
                self.assertEqual(_get_env_or_docker_default("SECRET_KEY"), "supersecret")
                self.assertEqual(_get_env_or_docker_default("DEBUG"), "True")

                # Test key not in docker-compose
                self.assertIsNone(_get_env_or_docker_default("NON_EXISTENT_KEY"))

                # Test with default fallback provided to function
                self.assertEqual(_get_env_or_docker_default("NON_EXISTENT_KEY", "my_default"), "my_default")

    @patch.dict(os.environ, {"API_KEY": "env_provided_key"}, clear=True)
    def test_get_env_or_docker_default_precedence(self):
        # Env var should take precedence over docker-compose
        docker_compose_content = "API_KEY=${API_KEY:-docker_default}"

        with patch("builtins.open", mock_open(read_data=docker_compose_content)):
            with patch("os.path.exists", return_value=True):
                self.assertEqual(_get_env_or_docker_default("API_KEY"), "env_provided_key")

    def test_handle_api_error(self):
        # Setup Flask app for testing
        app = Flask(__name__)
        app.config['TESTING'] = True

        # Mock logger to verify exception logging
        app.logger = MagicMock()

        @app.route('/api/error')
        @handle_api_error
        def error_route():
            raise ValueError("Test Exception")

        @app.route('/api/success')
        @handle_api_error
        def success_route():
            return {"status": "ok"}, 200

        client = app.test_client()

        # Test Error Case
        response = client.get('/api/error')
        self.assertEqual(response.status_code, 500)
        self.assertTrue(response.is_json)
        self.assertEqual(response.json, {"error": "Test Exception"})

        # Verify logger was called
        app.logger.exception.assert_called()
        args, _ = app.logger.exception.call_args
        self.assertIn("API Error in error_route: Test Exception", args[0])

        # Test Success Case
        response_success = client.get('/api/success')
        self.assertEqual(response_success.status_code, 200)
        self.assertEqual(response_success.json, {"status": "ok"})

if __name__ == '__main__':
    unittest.main()
