import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@patch('option_auditor.screener.screen_trend_followers_isa')
def test_check_isa_stock_with_entry_hold(mock_screen, client):
    # Mock return value: Signal is ENTER (Breakout), but we provide entry price
    # So we expect "HOLD"
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 150.0,
        "signal": "🚀 ENTER LONG",
        "trailing_exit_20d": 140.0,
        "trend_200sma": "Bullish"
    }]

    response = client.get('/screen/isa/check?ticker=AAPL&entry_price=145')
    data = response.get_json()

    assert response.status_code == 200
    assert data['ticker'] == "AAPL"
    # Should override ENTER to HOLD because we are in position (entry provided)
    assert "HOLD" in data['signal']
    assert data['user_entry_price'] == 145.0
    assert data['pnl_value'] == 5.0 # 150 - 145

@patch('option_auditor.screener.screen_trend_followers_isa')
def test_check_isa_stock_with_entry_exit(mock_screen, client):
    # Case: Price below exit
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 139.0,
        "signal": "✅ HOLD",
        "trailing_exit_20d": 140.0,
        "trend_200sma": "Bullish"
    }]

    # Here price 139 < 140. The logic in app.py should force EXIT
    response = client.get('/screen/isa/check?ticker=AAPL&entry_price=150')
    data = response.get_json()

    assert "EXIT" in data['signal']
    assert "Stop Hit" in data['signal']

@patch('option_auditor.screener.screen_trend_followers_isa')
def test_check_isa_stock_downtrend_exit(mock_screen, client):
    # Case: Downtrend
    mock_screen.return_value = [{
        "ticker": "TSLA",
        "price": 100.0,
        "signal": "❌ SELL/AVOID",
        "trailing_exit_20d": 90.0,
        "trend_200sma": "Bearish"
    }]

    response = client.get('/screen/isa/check?ticker=TSLA&entry_price=110')
    data = response.get_json()

    assert "EXIT" in data['signal']
    assert "Downtrend" in data['signal']

@patch('option_auditor.screener.screen_trend_followers_isa')
def test_check_isa_stock_no_entry_default(mock_screen, client):
    # Case: No entry price provided -> Default Logic
    mock_screen.return_value = [{
        "ticker": "NVDA",
        "price": 500.0,
        "signal": "🚀 ENTER LONG",
        "trailing_exit_20d": 480.0
    }]

    response = client.get('/screen/isa/check?ticker=NVDA')
    data = response.get_json()

    assert "ENTER LONG" in data['signal']
    assert 'user_entry_price' not in data
