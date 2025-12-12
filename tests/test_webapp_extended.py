import pytest
import json
import uuid
import time
import io
from unittest.mock import patch, MagicMock, ANY
from webapp.app import create_app, get_cached_screener_result, cache_screener_result, SCREENER_CACHE, _get_env_or_docker_default, send_email_notification

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_storage():
    with patch('webapp.app.get_storage_provider') as mock:
        yield mock

def test_cache_logic():
    # Test caching mechanism directly
    SCREENER_CACHE.clear()
    key = "test_key"
    data = {"test": "data"}

    # Cache miss
    assert get_cached_screener_result(key) is None

    # Cache hit
    cache_screener_result(key, data)
    assert get_cached_screener_result(key) == data

    # Cache expiration - Manual injection
    # We simulate an old entry
    old_timestamp = time.time() - 2000 # Older than 600s
    SCREENER_CACHE[key] = (old_timestamp, data)

    assert get_cached_screener_result(key) is None

def test_env_or_docker_default():
    # Test environment variable priority
    with patch.dict('os.environ', {'TEST_KEY': 'env_value'}):
        assert _get_env_or_docker_default('TEST_KEY', 'default') == 'env_value'

    # Test default fallback
    assert _get_env_or_docker_default('NON_EXISTENT_KEY', 'default') == 'default'

    # Test docker-compose parsing (mock file read)
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "TEST_KEY=${TEST_KEY:-docker_value}"
        with patch('os.path.exists', return_value=True):
             assert _get_env_or_docker_default('TEST_KEY', 'default') == 'docker_value'

@patch('webapp.app.resend')
def test_send_email_notification(mock_resend):
    # Missing API Key
    with patch('webapp.app._get_env_or_docker_default', return_value=None):
        send_email_notification("Subject", "Body")
        mock_resend.Emails.send.assert_not_called()

    # Success
    with patch('webapp.app._get_env_or_docker_default', return_value="fake_key"):
        mock_resend.Emails.send.return_value = {'id': '123'}
        send_email_notification("Subject", "Body")
        mock_resend.Emails.send.assert_called_once()

def test_feedback_route(client, mock_storage):
    # Valid feedback
    with patch('webapp.app.send_email_notification') as mock_email:
        res = client.post('/feedback', data={'message': 'Great app!', 'name': 'John', 'email': 'john@example.com'})
        assert res.status_code == 200
        mock_storage.return_value.save_feedback.assert_called_once()

    # Empty message
    res = client.post('/feedback', data={'message': ''})
    assert res.status_code == 400

def test_dashboard_route_no_session(client):
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert "No portfolio found" in res.json['error']

def test_dashboard_route_with_data(client, mock_storage):
    # Mock portfolio data
    mock_data = json.dumps({"test": "data"}).encode('utf-8')
    mock_storage.return_value.get_portfolio.return_value = mock_data

    with patch('webapp.app.refresh_dashboard_data') as mock_refresh:
        mock_refresh.return_value = {"test": "refreshed"}
        res = client.get('/dashboard')
        assert res.status_code == 200
        assert res.json == {"test": "refreshed"}

def test_health_route(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.data == b"OK"

def test_screen_route_params(client):
    with patch('option_auditor.screener.screen_market') as mock_screen:
        mock_screen.return_value = {}
        with patch('option_auditor.screener.screen_sectors') as mock_sectors:
             mock_sectors.return_value = []

             res = client.post('/screen', data={'iv_rank': '40', 'rsi_threshold': '60', 'time_frame': '1wk'})
             assert res.status_code == 200
             mock_screen.assert_called_with(40.0, 60.0, '1wk', region='us')

def test_screen_routes_specific(client):
    # Test Turtle
    with patch('option_auditor.screener.screen_turtle_setups') as mock_turtle:
        mock_turtle.return_value = []
        res = client.get('/screen/turtle?region=uk_euro')
        assert res.status_code == 200

    # Test Bull Put
    with patch('option_auditor.screener.screen_bull_put_spreads') as mock_bull:
        mock_bull.return_value = []
        res = client.get('/screen/bull_put')
        assert res.status_code == 200

    # Test MMS
    with patch('option_auditor.screener.screen_mms_ote_setups') as mock_mms:
        mock_mms.return_value = []
        res = client.get('/screen/mms?time_frame=15m')
        assert res.status_code == 200

def test_journal_routes(client, mock_storage):
    # Add
    mock_storage.return_value.save_journal_entry.return_value = "123"
    res = client.post('/journal/add', json={"symbol": "AAPL"})
    assert res.status_code == 200
    assert res.json['id'] == "123"

    # Delete
    res = client.delete('/journal/delete/123')
    assert res.status_code == 200
    mock_storage.return_value.delete_journal_entry.assert_called_with(ANY, "123")

    # Import
    mock_storage.return_value.save_journal_entries.return_value = 1
    res = client.post('/journal/import', json=[{"symbol": "AAPL", "pnl": 100}])
    assert res.status_code == 200
    assert res.json['count'] == 1
    mock_storage.return_value.save_journal_entries.assert_called()

    # Analyze
    mock_storage.return_value.get_journal_entries.return_value = []
    with patch('webapp.app.journal_analyzer.analyze_journal') as mock_analyze:
        mock_analyze.return_value = {}
        res = client.post('/journal/analyze')
        assert res.status_code == 200

def test_analyze_route_manual(client, mock_storage):
    manual_data = json.dumps([{"date": "2023-01-01", "symbol": "AAPL", "action": "BUY", "quantity": 10, "price": 150}])
    # Patch where it is imported in webapp/app.py
    with patch('webapp.app.analyze_csv') as mock_analyze:
        mock_analyze.return_value = {"results": "success"}

        res = client.post('/analyze', data={
            'manual_trades': manual_data,
            'account_size_start': '10000',
            'style': 'speculation'
        })

        assert res.status_code == 200
        mock_analyze.assert_called()
        assert mock_analyze.call_args[1]['manual_data'] is not None

def test_analyze_route_file(client, mock_storage):
    data = {'csv': (io.BytesIO(b"date,symbol,action\n2023-01-01,AAPL,BUY"), 'test.csv')}
    # Patch where it is imported in webapp/app.py
    with patch('webapp.app.analyze_csv') as mock_analyze:
        mock_analyze.return_value = {"results": "success", "excel_report": io.BytesIO(b"excel")}

        res = client.post('/analyze', data=data, content_type='multipart/form-data')

        assert res.status_code == 200
        mock_storage.return_value.save_report.assert_called() # Should save excel
        mock_storage.return_value.save_portfolio.assert_called()

def test_download_route(client, mock_storage):
    mock_storage.return_value.get_report.return_value = b"file_content"
    res = client.get('/download/token123/report.xlsx')
    assert res.status_code == 200
    assert res.data == b"file_content"

    mock_storage.return_value.get_report.return_value = None
    res = client.get('/download/token123/missing.xlsx')
    assert res.status_code == 404

def test_cleanup_job():
    # Test cleanup job logic (mock storage)
    app = create_app(testing=True)
    # Patch _get_storage_provider because cleanup_job calls it directly
    with patch('webapp.app._get_storage_provider') as mock_storage_prov:
        with patch('time.sleep', side_effect=InterruptedError): # Break loop
            try:
                # Import cleanup_job function locally to test
                from webapp.app import cleanup_job
                cleanup_job(app)
            except InterruptedError:
                pass
        mock_storage_prov.return_value.cleanup_old_reports.assert_called()
