import pytest
import json
from webapp.app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

def test_safety_score_endpoint(client, mocker):
    # Mock external calls to avoid real API/cache hits in portfolio_risk
    mocker.patch('option_auditor.portfolio_risk.get_cached_market_data', return_value={})

    positions = [
        {'ticker': 'A', 'value': 10},
        {'ticker': 'B', 'value': 90} # 90/100 = 90%
    ]
    response = client.post('/safety/score', json={'positions': positions})
    assert response.status_code == 200
    data = response.get_json()
    assert 'score' in data
    # Concentration penalty: 5 points for A (10%), 5 points for B (90%). Total -10. Score 90.
    # But wait, 10/100 = 10% (>5%). 90/100 = 90% (>5%).
    assert data['score'] < 100

def test_check_allocation_endpoint(client):
    positions = [
        {'ticker': 'A', 'value': 60}, # 6% of 1000
        {'ticker': 'B', 'value': 940} # 94% of 1000
    ]
    response = client.post('/safety/check-allocation', json={'positions': positions})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert any(d['ticker'] == 'A' for d in data)
    assert any(d['ticker'] == 'B' for d in data)

def test_what_if_endpoint(client, mocker):
    # Mock portfolio_risk.analyze_scenario if needed, or rely on simple equity logic
    positions = [{'ticker': 'A', 'value': 1000}]
    response = client.post('/safety/what-if', json={'positions': positions})
    assert response.status_code == 200
    data = response.get_json()
    assert 'pnl' in data
    assert data['pnl'] == -100.0 # 10% of 1000
    assert data['pnl_pct'] == -10.0
