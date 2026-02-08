import pytest
from unittest.mock import patch, MagicMock

# Note: The 'client' fixture is provided by tests/conftest.py

def test_screen_universal_success(client):
    """Test /screen/universal endpoint with valid results."""

    mock_results = {
        "regime": "Bullish",
        "results": [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "price": 150.0,
                "master_verdict": "BUY",
                "action": "BUY 100 QTY",
                "stop_loss": 140.0,
                "vol_scan": "Low",
                "rsi": 60.0,
                "quality_score": 80.0,
                "master_color": "green",
                "breakout_date": "2023-10-27"
            },
            {
                "ticker": "TSLA",
                "company_name": "Tesla Inc.",
                "price": 200.0,
                "master_verdict": "WATCH",
                "action": "WAIT",
                "stop_loss": 190.0,
                "vol_scan": "High",
                "rsi": 45.0,
                "quality_score": 60.0,
                "master_color": "yellow",
                "breakout_date": "2023-10-28"
            }
        ]
    }

    # Mock get_cached_screener_result to return None to bypass cache
    with patch('option_auditor.screener.screen_universal_dashboard', return_value=mock_results) as mock_screen, \
         patch('webapp.blueprints.screener_routes.get_cached_screener_result', return_value=None):

        response = client.get('/screen/universal?region=us')

        assert response.status_code == 200
        data = response.get_json()

        assert data['regime'] == "Bullish"
        assert len(data['results']) == 2

        # Verify first result metadata
        aapl = data['results'][0]
        assert aapl['ticker'] == "AAPL"
        assert aapl['master_verdict'] == "BUY"
        assert aapl['master_color'] == "green"

        # Verify mock call
        mock_screen.assert_called_once()


def test_screen_universal_empty(client):
    """Test /screen/universal with empty results."""
    mock_results = {"regime": "Neutral", "results": []}

    # Mock get_cached_screener_result to return None
    with patch('option_auditor.screener.screen_universal_dashboard', return_value=mock_results), \
         patch('webapp.blueprints.screener_routes.get_cached_screener_result', return_value=None):

        response = client.get('/screen/universal?region=us')
        assert response.status_code == 200
        data = response.get_json()
        assert data['results'] == []


def test_screen_market_success(client):
    """Test /screen POST endpoint."""
    mock_market_results = {
        "Technology": [{"ticker": "AAPL", "rsi": 60}],
        "Energy": [{"ticker": "XOM", "rsi": 40}]
    }
    mock_sector_results = {"Technology": 1.5, "Energy": -0.5}

    with patch('option_auditor.screener.screen_market', return_value=mock_market_results) as mock_screen_market, \
         patch('option_auditor.screener.screen_sectors', return_value=mock_sector_results) as mock_screen_sectors, \
         patch('webapp.blueprints.screener_routes.get_cached_screener_result', return_value=None):

        response = client.post('/screen', data={
            'region': 'us',
            'time_frame': '1d',
            'iv_rank': 30,
            'rsi_threshold': 50
        })

        assert response.status_code == 200
        data = response.get_json()

        assert 'results' in data
        assert 'sector_results' in data
        assert data['results']['Technology'][0]['ticker'] == "AAPL"

        mock_screen_market.assert_called_once()
        mock_screen_sectors.assert_called_once()

def test_screen_turtle_success(client):
    """Test /screen/turtle endpoint."""
    mock_results = [
        {"ticker": "NVDA", "signal": "BUY", "price": 400.0},
        {"ticker": "AMD", "signal": "SELL", "price": 100.0}
    ]

    with patch('option_auditor.screener.screen_turtle_setups', return_value=mock_results):
        response = client.get('/screen/turtle?region=us')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]['ticker'] == "NVDA"

def test_screen_isa_check(client):
    """Test /screen/isa/check endpoint."""
    mock_results = [{
        "ticker": "AAPL",
        "price": 150.0,
        "signal": "ENTER",
        "trailing_exit_20d": 140.0
    }]

    with patch('option_auditor.screener.screen_trend_followers_isa', return_value=mock_results):
        # Test with entry price
        response = client.get('/screen/isa/check?ticker=AAPL&entry_price=145.0')
        assert response.status_code == 200
        data = response.get_json()

        assert data['ticker'] == "AAPL"
        assert data['user_entry_price'] == 145.0
        assert 'pnl_pct' in data
        assert data['signal'] == "✅ HOLD (Trend Active)"

def test_screen_isa_check_not_found(client):
    """Test /screen/isa/check with no results."""
    with patch('option_auditor.screener.screen_trend_followers_isa', return_value=[]):
        response = client.get('/screen/isa/check?ticker=INVALID')
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
