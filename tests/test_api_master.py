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
    # However, `webapp.app` uses `screener.screen_universal_dashboard` from `option_auditor.screener`.
    # And `option_auditor.screener` imports it from `option_auditor.unified_screener`.
    # So we patch `option_auditor.screener.screen_universal_dashboard` or `option_auditor.unified_screener.screen_universal_dashboard`.
    # Since `webapp.app` calls `screener.screen_universal_dashboard`, we patch that.

    # Patch the function imported in webapp.app
    with patch('webapp.app.screen_master_convergence') as mock_screen:
        # It returns a list of dicts
        mock_screen.return_value = [{"ticker": "TEST", "master_verdict": "ISA_BUY", "price": 100}]

        # Test US Region
        resp = client.get("/screen/master?region=us")
        assert resp.status_code == 200
        data = resp.json

        # Verify structure: direct list
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['ticker'] == "TEST"

        # Verify call args
        mock_screen.assert_called()

def test_screen_master_endpoint_uk(client):
    with patch('webapp.app.screen_master_convergence') as mock_screen:
        mock_screen.return_value = []

        resp = client.get("/screen/master?region=uk")
        assert resp.status_code == 200

        # Verify called with region='uk'
        mock_screen.assert_called_with(region='uk')
