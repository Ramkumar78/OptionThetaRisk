import pytest
from flask import Flask
from webapp.app import create_app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == "OK"

@patch('webapp.app.resend.Emails.send')
def test_feedback_endpoint(mock_send, client):
    mock_send.return_value = {'id': '123'}

    # Test valid feedback
    response = client.post('/feedback', data={
        'message': 'Great app!',
        'name': 'Test User',
        'email': 'test@example.com'
    })
    assert response.status_code == 200
    assert response.get_json()['success'] is True

    # Test missing feedback
    response = client.post('/feedback', data={})
    assert response.status_code == 400
    assert 'Message cannot be empty' in response.get_json()['error']

@patch('webapp.app.get_storage_provider')
def test_dashboard_endpoint_no_portfolio(mock_get_storage, client):
    mock_db = MagicMock()
    mock_db.get_portfolio.return_value = None
    mock_get_storage.return_value = mock_db

    with client.session_transaction() as sess:
        sess['username'] = 'test_user'

    response = client.get('/dashboard')
    assert response.status_code == 200
    assert response.get_json()['error'] == 'No portfolio found'

@patch('webapp.app.get_storage_provider')
@patch('webapp.app.refresh_dashboard_data')
def test_dashboard_endpoint_with_portfolio(mock_refresh, mock_get_storage, client):
    mock_db = MagicMock()
    mock_db.get_portfolio.return_value = b'{"total_pnl": 1000}'
    mock_get_storage.return_value = mock_db

    mock_refresh.return_value = {'total_pnl': 1000}

    with client.session_transaction() as sess:
        sess['username'] = 'test_user'

    response = client.get('/dashboard')
    assert response.status_code == 200
    assert response.get_json()['total_pnl'] == 1000

@patch('webapp.app.screener.screen_market')
@patch('webapp.app.screener.screen_sectors')
def test_screen_market_endpoint(mock_sectors, mock_market, client):
    mock_market.return_value = {"Tech": []}
    mock_sectors.return_value = []

    response = client.post('/screen', data={'iv_rank': '20', 'rsi_threshold': '60'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'results' in data
    assert 'sector_results' in data
    mock_market.assert_called_with(20.0, 60.0, '1d', tasty_creds=None)
