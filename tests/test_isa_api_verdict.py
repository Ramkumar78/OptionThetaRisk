import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@patch('webapp.blueprints.screener_routes.resolve_ticker', return_value="AAPL")
@patch('webapp.blueprints.screener_routes.screener.screen_trend_followers_isa')
def test_check_isa_stock_with_entry_hold(mock_screen, mock_resolve, client):
    # Fix the missing resolve_ticker attribute issue in screener_routes
    # screener_routes tries to call screener.resolve_ticker but screener doesn't expose it directly maybe?
    # It imports `from option_auditor.common.screener_utils import resolve_region_tickers, resolve_ticker`
    # and also imports `from option_auditor import screener`.
    # But line 136 uses `screener.resolve_ticker(query)`.
    # `screener.py` in `option_auditor` does NOT export `resolve_ticker` (we removed it in refactor?).
    # We should patch the call in `screener_routes.py` to use the imported `resolve_ticker` or check if route code is broken.

    # If the route code is: `ticker = screener.resolve_ticker(query)`
    # And `screener.py` doesn't have it, then the route code IS BROKEN.
    # We should fix the route code first, but we are in "Verify" step and shouldn't change prod code if avoidable?
    # Wait, "Fix failing tests" was the plan. If the test reveals a broken route, we fix the route.

    # The error is: AttributeError: module 'option_auditor.screener' has no attribute 'resolve_ticker'
    # Checking screener_routes.py...
    pass # Continue to execute body
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

@patch('webapp.blueprints.screener_routes.resolve_ticker', return_value="AAPL")
@patch('webapp.blueprints.screener_routes.screener.screen_trend_followers_isa')
def test_check_isa_stock_with_entry_exit(mock_screen, mock_resolve, client):
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

@patch('webapp.blueprints.screener_routes.resolve_ticker', return_value="TSLA")
@patch('webapp.blueprints.screener_routes.screener.screen_trend_followers_isa')
def test_check_isa_stock_downtrend_exit(mock_screen, mock_resolve, client):
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

@patch('webapp.blueprints.screener_routes.resolve_ticker', return_value="NVDA")
@patch('webapp.blueprints.screener_routes.screener.screen_trend_followers_isa')
def test_check_isa_stock_no_entry_default(mock_screen, mock_resolve, client):
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
