import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_analyze_market_data_success(client):
    """Test that valid ticker returns correctly formatted JSON."""

    # Mock DataFrame
    dates = pd.date_range(start="2023-01-01", periods=2)
    data = {
        'Open': [100.0, 102.0],
        'High': [105.0, 106.0],
        'Low': [99.0, 101.0],
        'Close': [102.0, 104.0],
        'Volume': [1000, 2000]
    }
    # Create MultiIndex to match fetch_batch_data_safe behavior for list
    df = pd.DataFrame(data, index=dates)
    df.columns = pd.MultiIndex.from_product([['SPY'], df.columns])

    with patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe', return_value=df) as mock_fetch:
        response = client.post('/analyze/market-data', json={'ticker': 'SPY'})

        assert response.status_code == 200
        json_data = response.get_json()
        assert len(json_data) == 2
        assert json_data[0]['time'] == '2023-01-01'
        assert json_data[0]['open'] == 100.0
        assert json_data[0]['close'] == 102.0

def test_analyze_market_data_missing_ticker(client):
    response = client.post('/analyze/market-data', json={})
    assert response.status_code == 400
    assert "Ticker required" in response.get_json()['error']

def test_analyze_market_data_empty(client):
    with patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe', return_value=pd.DataFrame()):
        response = client.post('/analyze/market-data', json={'ticker': 'BAD'})
        assert response.status_code == 404
