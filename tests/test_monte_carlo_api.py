import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify, request
from webapp.blueprints.analysis_routes import analysis_bp
from option_auditor.unified_backtester import UnifiedBacktester

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(analysis_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_monte_carlo_api_invalid_simulations(mock_backtester, client):
    # Test valid input
    mock_instance = MagicMock()
    mock_instance.run_monte_carlo.return_value = {"success": True}
    mock_backtester.return_value = mock_instance

    resp = client.post("/analyze/monte-carlo", json={"ticker": "SPY", "simulations": "100"})
    assert resp.status_code == 200

    # Test invalid simulations input
    resp = client.post("/analyze/monte-carlo", json={"ticker": "SPY", "simulations": "invalid"})
    assert resp.status_code == 400
    json_resp = resp.get_json()
    assert "Validation Error" in json_resp["error"]
    assert any("simulations" in str(d["loc"]) for d in json_resp["details"])
