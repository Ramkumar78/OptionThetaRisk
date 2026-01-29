import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('webapp.blueprints.analysis_routes.calculate_correlation_matrix')
def test_correlation_endpoint_success(mock_calc, client):
    mock_calc.return_value = {
        "tickers": ["AAPL", "MSFT"],
        "matrix": [[1.0, 0.5], [0.5, 1.0]],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31"
    }

    response = client.post('/analyze/correlation', json={"tickers": ["AAPL", "MSFT"]})

    assert response.status_code == 200
    data = response.get_json()
    assert data['tickers'] == ["AAPL", "MSFT"]
    assert len(data['matrix']) == 2

@patch('webapp.blueprints.analysis_routes.calculate_correlation_matrix')
def test_correlation_endpoint_error(mock_calc, client):
    mock_calc.return_value = {"error": "Insufficient data"}

    response = client.post('/analyze/correlation', json={"tickers": ["A"]})

    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == "Insufficient data"
