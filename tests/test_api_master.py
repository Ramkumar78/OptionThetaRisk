import pytest
from unittest.mock import patch, MagicMock
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_screen_master_endpoint(client):
    # Mock screen_universal_dashboard
    # Note: app.py imports it from option_auditor.unified_screener
    # but uses it as `screen_universal_dashboard`.

    # Correct mock path based on import in app.py:
    # `from option_auditor.unified_screener import screen_universal_dashboard`
    # So we patch `webapp.app.screen_universal_dashboard`

    with patch('webapp.app.screen_universal_dashboard') as mock_screen:
        # It now returns a dict
        mock_screen.return_value = {
            "regime": "GREEN",
            "results": [{"ticker": "TEST", "master_verdict": "ISA_BUY", "price": 100}]
        }

        # Test US Region
        resp = client.get("/screen/master?region=us")
        assert resp.status_code == 200
        data = resp.json

        # Verify structure
        assert "regime" in data
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]['ticker'] == "TEST"

        # Verify call args
        args, kwargs = mock_screen.call_args
        # It takes ticker_list as kwarg or arg
        assert kwargs['ticker_list'] is not None

def test_screen_master_endpoint_uk(client):
    with patch('webapp.app.screen_universal_dashboard') as mock_screen:
        mock_screen.return_value = {"regime": "GREEN", "results": []}

        # Patch get_tickers_for_region inside app
        with patch('webapp.app.get_tickers_for_region') as mock_get_tickers:
            mock_get_tickers.return_value = ["BP.L"]

            resp = client.get("/screen/master?region=uk")
            assert resp.status_code == 200

            # Verify screen_universal_dashboard called with BP.L
            mock_screen.assert_called_once_with(ticker_list=["BP.L"])
