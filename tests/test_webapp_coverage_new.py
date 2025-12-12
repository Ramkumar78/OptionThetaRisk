import unittest
from unittest.mock import patch, MagicMock
import json
import io
from webapp.app import create_app
import pytest

class TestWebappCoverageNew(unittest.TestCase):
    def setUp(self):
        self.app = create_app(testing=True)
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Setup session
        with self.client.session_transaction() as sess:
            sess['username'] = 'testuser'

    def test_health_check(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), "OK")

    def test_upload_too_large(self):
        # We can't easily trigger 413 without sending a large payload,
        # but we can invoke the handler if it's registered.
        # Alternatively, we set MAX_CONTENT_LENGTH low and send slightly larger.
        self.app.config['MAX_CONTENT_LENGTH'] = 10  # 10 bytes
        response = self.client.post('/analyze', data={'csv': (io.BytesIO(b'a' * 20), 'test.csv')})
        # Flask 413 handling might return HTML by default or JSON if configured.
        # Our handler returns JSON.
        # Note: Test client might not enforce MAX_CONTENT_LENGTH the same way real server does
        # unless we are careful.
        # Usually client raises RequestEntityTooLarge error or returns 413.
        self.assertEqual(response.status_code, 413)
        self.assertIn("Upload too large", response.get_json()['error'])

    @patch('webapp.app.get_storage_provider')
    def test_download_file_found(self, mock_get_storage):
        mock_storage = MagicMock()
        mock_storage.get_report.return_value = b"file content"
        mock_get_storage.return_value = mock_storage

        response = self.client.get('/download/token123/report.xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"file content")
        self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=report.xlsx')

    @patch('webapp.app.get_storage_provider')
    def test_download_file_not_found(self, mock_get_storage):
        mock_storage = MagicMock()
        mock_storage.get_report.return_value = None
        mock_get_storage.return_value = mock_storage

        response = self.client.get('/download/token123/missing.xlsx')
        self.assertEqual(response.status_code, 404)

    @patch('webapp.app.screener.screen_market')
    @patch('webapp.app.screener.screen_sectors')
    def test_screen_market_params(self, mock_sectors, mock_market):
        mock_market.return_value = {"market": "data"}
        mock_sectors.return_value = []

        # Test defaults
        self.client.post('/screen')
        mock_market.assert_called_with(30.0, 50.0, "1d", region="us")

        # Test params
        self.client.post('/screen', data={"iv_rank": "50", "rsi_threshold": "70", "time_frame": "1wk", "region": "sp500"})
        mock_market.assert_called_with(50.0, 70.0, "1wk", region="sp500")

    @patch('webapp.app.screener.screen_turtle_setups')
    def test_screen_turtle_params(self, mock_turtle):
        mock_turtle.return_value = []

        self.client.get('/screen/turtle?region=india&time_frame=1wk')
        # Check args passed to screen_turtle_setups
        # The route calls get_indian_tickers etc inside.
        # We just verify it returns 200.
        self.assertEqual(mock_turtle.call_count, 1)

    @patch('webapp.app.screener.screen_darvas_box')
    def test_screen_darvas_sp500(self, mock_darvas):
         mock_darvas.return_value = []
         # Ensure SP500 path is taken
         with patch('webapp.app.screener._get_filtered_sp500', return_value=["AAPL"]):
             self.client.get('/screen/darvas?region=sp500')
             self.assertEqual(mock_darvas.call_count, 1)

    def test_static_files(self):
        # Setup dummy file in static/react_build
        import os
        build_dir = os.path.join(self.app.static_folder, "react_build")
        os.makedirs(build_dir, exist_ok=True)
        with open(os.path.join(build_dir, "test.txt"), "w") as f:
            f.write("static content")

        response = self.client.get('/test.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"static content")

        # Clean up
        os.remove(os.path.join(build_dir, "test.txt"))

    def test_catch_all_route(self):
        # Should return index.html for unknown routes (React Router)
        # Assuming index.html exists or is mocked?
        # create_app doesn't create index.html.
        # We need to ensure it exists for the test or mock send_from_directory

        with patch('webapp.app.send_from_directory') as mock_send:
             mock_send.return_value = "index.html content"
             response = self.client.get('/some/react/route')
             self.assertEqual(response.data, b"index.html content")

    @patch('webapp.app.get_storage_provider')
    def test_journal_import_invalid(self, mock_storage):
        response = self.client.post('/journal/import', json={}) # Not a list
        self.assertEqual(response.status_code, 400)

    @patch('webapp.app.get_storage_provider')
    def test_journal_add_no_data(self, mock_storage):
        # Sending json=None usually implies no body, but content-type might be wrong?
        # If we send empty dict it is valid json but empty data.
        # If we explicitly send data=None and content_type application/json
        response = self.client.post('/journal/add', data=None, content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
