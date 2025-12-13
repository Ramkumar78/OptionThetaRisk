
import json
import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_fourier_route(client):
    """Test the /screen/fourier endpoint."""
    mock_data = [
        {"ticker": "AAPL", "cycle_period": "20 Days", "cycle_position": "-0.9 (Low)"}
    ]

    with patch('option_auditor.screener.screen_fourier_cycles', return_value=mock_data) as mock_screen:
        # 1. Test basic call
        resp = client.get("/screen/fourier")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json == mock_data

        # Verify default args
        mock_screen.assert_called_with(ticker_list=None, time_frame="1d")

        # 2. Test with params
        resp = client.get("/screen/fourier?region=uk_euro&time_frame=1wk")
        assert resp.status_code == 200
        assert resp.json == mock_data

        # Verify args passed (ticker list would be mocked in real app but here checking flow)
        # Note: We can't easily verify ticker_list content without mocking get_uk_euro_tickers too,
        # but we can verify time_frame.
        args, kwargs = mock_screen.call_args
        assert kwargs['time_frame'] == "1wk"

def test_darvas_route(client):
    """Test the /screen/darvas endpoint."""
    mock_data = [{"ticker": "NVDA", "signal": "BREAKOUT"}]
    with patch('option_auditor.screener.screen_darvas_box', return_value=mock_data):
        resp = client.get("/screen/darvas")
        assert resp.status_code == 200
        assert resp.json == mock_data

def test_mms_route(client):
    """Test the /screen/mms endpoint."""
    mock_data = [{"ticker": "AMD", "signal": "BULLISH OTE"}]
    with patch('option_auditor.screener.screen_mms_ote_setups', return_value=mock_data):
        resp = client.get("/screen/mms")
        assert resp.status_code == 200
        assert resp.json == mock_data
