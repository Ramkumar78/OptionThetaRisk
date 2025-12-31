import pytest
from unittest.mock import patch, MagicMock
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_screen_master_endpoint(client):
    # Mock MasterScreener class
    with patch('webapp.app.MasterScreener') as MockScreener:
        instance = MockScreener.return_value
        instance.run.return_value = [
            {"Ticker": "TEST", "Type": "ISA_BUY", "Price": 100}
        ]

        # Test US Region
        resp = client.get("/screen/master?region=us")
        assert resp.status_code == 200
        data = resp.json
        assert len(data) == 1
        assert data[0]['Ticker'] == "TEST"

        # Verify call args
        args, _ = MockScreener.call_args
        # args[0] is us_tickers, args[1] is uk_tickers
        # US region should have items in us_tickers and empty uk_tickers

        assert len(args[0]) > 0
        assert len(args[1]) == 0

def test_screen_master_endpoint_uk(client):
    with patch('webapp.app.MasterScreener') as MockScreener:
        instance = MockScreener.return_value
        instance.run.return_value = []

        # Patch get_uk_tickers to ensure it returns something we can verify
        with patch('webapp.app.get_uk_tickers') as mock_uk:
            mock_uk.return_value = ["BP.L"]

            resp = client.get("/screen/master?region=uk")
            assert resp.status_code == 200

            args, _ = MockScreener.call_args
            assert len(args[0]) == 0 # US tickers empty
            assert "BP.L" in args[1]
