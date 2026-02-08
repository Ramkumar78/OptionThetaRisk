import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from flask import Flask, jsonify
from webapp.utils import _allowed_filename, _get_env_or_docker_default, handle_api_error

class TestWebUtils(unittest.TestCase):

    def test_allowed_filename(self):
        # Case sensitivity
        self.assertTrue(_allowed_filename("data.csv"))
        self.assertTrue(_allowed_filename("DATA.CSV"))
        self.assertTrue(_allowed_filename("Mixed.Csv"))

        # Various extensions
        self.assertFalse(_allowed_filename("data.txt"))
        self.assertFalse(_allowed_filename("image.png"))
        self.assertFalse(_allowed_filename("document.pdf"))
        self.assertFalse(_allowed_filename("script.py"))

        # No extension
        self.assertFalse(_allowed_filename("data"))
        self.assertFalse(_allowed_filename(""))

    @patch('webapp.utils.os.environ')
    def test_get_env_or_docker_default_env_var(self, mock_environ):
        mock_environ.get.return_value = "env_value"
        self.assertEqual(_get_env_or_docker_default("TEST_KEY"), "env_value")

    @patch('webapp.utils.os.environ')
    def test_get_env_or_docker_default_docker_compose(self, mock_environ):
        mock_environ.get.return_value = None

        docker_content = """
        version: '3.8'
        services:
          web:
            environment:
              - TEST_KEY=${TEST_KEY:-docker_value}
              - OTHER_KEY=${OTHER_KEY:-other_value}
        """

        with patch('webapp.utils.os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=docker_content)):
                self.assertEqual(_get_env_or_docker_default("TEST_KEY"), "docker_value")
                self.assertEqual(_get_env_or_docker_default("OTHER_KEY"), "other_value")

    @patch('webapp.utils.os.environ')
    def test_get_env_or_docker_default_fallback(self, mock_environ):
        mock_environ.get.return_value = None

        # File exists but no match
        docker_content = "NO_MATCHING_KEY=value"
        with patch('webapp.utils.os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=docker_content)):
                self.assertEqual(_get_env_or_docker_default("TEST_KEY", "default"), "default")

        # File does not exist
        with patch('webapp.utils.os.path.exists', return_value=False):
             self.assertEqual(_get_env_or_docker_default("TEST_KEY", "default"), "default")

    def test_handle_api_error(self):
        app = Flask(__name__)

        @app.route('/test')
        @handle_api_error
        def error_route():
            raise ValueError("Test Error")

        with app.test_request_context('/test'):
             # We need to mock current_app.logger because handle_api_error uses it
             with patch('webapp.utils.current_app') as mock_app:
                 # Ensure logger is a standard MagicMock, not AsyncMock
                 mock_app.logger = MagicMock()
                 response, status_code = error_route()

                 self.assertEqual(status_code, 500)
                 self.assertEqual(response.json, {"error": "Test Error"})
                 mock_app.logger.exception.assert_called()

if __name__ == '__main__':
    unittest.main()
