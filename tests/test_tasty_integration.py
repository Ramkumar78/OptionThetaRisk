import pytest
from unittest.mock import MagicMock, patch
from flask import json

# Import the app factory
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        with app.app_context():
            yield client

@patch('webapp.app.Session')
def test_tastytrade_connect_success(mock_session_cls, client):
    # Setup Mock
    mock_instance = MagicMock()
    mock_instance.validate.return_value = True
    mock_session_cls.return_value = mock_instance

    # Execute
    response = client.post('/api/tastytrade/connect')

    # Verify
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert "CONNECTION ESTABLISHED" in data['message']

    # Verify Session Init called with Env Vars (mocked or from .env)
    assert mock_session_cls.called

@patch('webapp.app.Session')
def test_tastytrade_connect_failure(mock_session_cls, client):
    # Setup Mock
    mock_instance = MagicMock()
    mock_instance.validate.return_value = False
    mock_session_cls.return_value = mock_instance

    # Execute
    response = client.post('/api/tastytrade/connect')

    # Verify
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['success'] is False

@patch('webapp.app.Session')
@patch('webapp.app.Account')
def test_tastytrade_account_metrics(mock_account_cls, mock_session_cls, client):
    # 1. Connect first to set session
    mock_session_instance = MagicMock()
    mock_session_instance.validate.return_value = True
    mock_session_cls.return_value = mock_session_instance

    with client.session_transaction() as sess:
        sess['tt_active'] = True

    # 2. Setup Account Mocks
    mock_account = MagicMock()
    mock_account_cls.get_accounts.return_value = [mock_account]

    # Mock Balances
    mock_balances = MagicMock()
    mock_balances.net_liquidating_value = 10000.0
    mock_balances.derivative_buying_power = 4000.0
    mock_balances.used_derivative_buying_power = 6000.0
    mock_account.get_balances.return_value = mock_balances

    # Mock Positions
    mock_pos = MagicMock()
    mock_pos.symbol = "SPY"
    mock_pos.quantity = 10
    mock_pos.mark = 450.0
    mock_pos.expires_at = None
    mock_account.get_positions.return_value = [mock_pos]

    # Execute
    response = client.get('/api/tastytrade/account')

    # Verify
    assert response.status_code == 200
    data = json.loads(response.data)

    assert data['net_liq'] == 10000.0
    assert data['buying_power'] == 4000.0
    # BP Usage = (6000 / 10000) * 100 = 60.0
    assert data['bp_usage'] == 60.0
    assert len(data['positions']) == 1
    assert data['positions'][0]['symbol'] == "SPY"
