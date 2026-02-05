import pytest
from unittest.mock import patch
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_scenario')
def test_scenario_endpoint_success(mock_analyze, client):
    # Mock return value
    mock_analyze.return_value = {
        "current_value": 1000,
        "new_value": 1100,
        "pnl": 100,
        "pnl_pct": 10.0,
        "details": []
    }

    payload = {
        "positions": [{"ticker": "AAPL", "qty": 1}],
        "scenario": {"price_change_pct": 10}
    }

    response = client.post('/analyze/scenario', json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["pnl"] == 100
    mock_analyze.assert_called_once()

def test_scenario_endpoint_validation(client):
    # Missing positions
    payload = {
        "scenario": {"price_change_pct": 10}
    }
    response = client.post('/analyze/scenario', json=payload)
    assert response.status_code == 400
    json_resp = response.get_json()
    assert "Validation Error" in json_resp["error"]
    assert any("positions" in str(d["loc"]) for d in json_resp["details"])

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_scenario')
def test_scenario_endpoint_error_handling(mock_analyze, client):
    # Mock exception
    mock_analyze.side_effect = Exception("Something went wrong")

    payload = {
        "positions": [{"ticker": "AAPL", "qty": 1}],
        "scenario": {"price_change_pct": 10}
    }
    response = client.post('/analyze/scenario', json=payload)
    assert response.status_code == 500
    assert "Something went wrong" in response.get_json()["error"]
