import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from webapp.blueprints.analysis_routes import analysis_bp
import pandas as pd
import json

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(analysis_bp)
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

# --- Market Data Tests ---

@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_market_data_success_single_index(mock_fetch, client):
    dates = pd.date_range("2023-01-01", periods=2)
    df = pd.DataFrame({
        "Open": [100, 101],
        "High": [105, 106],
        "Low": [99, 100],
        "Close": [102, 103],
        "Volume": [1000, 1200]
    }, index=dates)

    mock_fetch.return_value = df

    resp = client.post("/analyze/market-data", json={"ticker": "AAPL"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]["close"] == 102

@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_market_data_success_multi_index(mock_fetch, client):
    dates = pd.date_range("2023-01-01", periods=2)

    iterables = [["AAPL"], ["Open", "High", "Low", "Close", "Volume"]]
    columns = pd.MultiIndex.from_product(iterables)

    df = pd.DataFrame(index=dates, columns=columns)
    df[("AAPL", "Open")] = [100, 101]
    df[("AAPL", "High")] = [105, 106]
    df[("AAPL", "Low")] = [99, 100]
    df[("AAPL", "Close")] = [102, 103]
    df[("AAPL", "Volume")] = [1000, 1200]

    mock_fetch.return_value = df

    resp = client.post("/analyze/market-data", json={"ticker": "AAPL"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]["close"] == 102

@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_market_data_empty(mock_fetch, client):
    mock_fetch.return_value = pd.DataFrame()
    resp = client.post("/analyze/market-data", json={"ticker": "AAPL"})
    assert resp.status_code == 404

def test_market_data_missing_ticker(client):
    resp = client.post("/analyze/market-data", json={})
    assert resp.status_code == 400

@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_market_data_structure_mismatch(mock_fetch, client):
    # MultiIndex but ticker not found
    dates = pd.date_range("2023-01-01", periods=2)
    iterables = [["GOOG"], ["Open"]]
    columns = pd.MultiIndex.from_product(iterables)
    df = pd.DataFrame(index=dates, columns=columns)

    mock_fetch.return_value = df

    resp = client.post("/analyze/market-data", json={"ticker": "AAPL"})
    assert resp.status_code == 500
    assert "not found in data structure" in resp.get_json()["error"]

# --- Greeks Tests ---

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_portfolio_greeks')
def test_greeks_success(mock_greeks, client):
    mock_greeks.return_value = {"delta": 100}
    resp = client.post("/analyze/portfolio/greeks", json={"positions": [{"ticker": "AAPL"}]})
    assert resp.status_code == 200
    assert resp.get_json()["delta"] == 100

def test_greeks_missing_positions(client):
    resp = client.post("/analyze/portfolio/greeks", json={})
    assert resp.status_code == 400

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_portfolio_greeks')
def test_greeks_error(mock_greeks, client):
    mock_greeks.side_effect = Exception("Calc Failed")
    resp = client.post("/analyze/portfolio/greeks", json={"positions": [{"ticker": "AAPL"}]})
    assert resp.status_code == 500
    assert "Calc Failed" in resp.get_json()["error"]

# --- Monte Carlo Tests (Extra) ---

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_monte_carlo_missing_ticker(mock_ub, client):
    resp = client.post("/analyze/monte-carlo", json={"simulations": 100})
    assert resp.status_code == 400
    # New validation error format
    assert "Validation Error" in resp.get_json()["error"]
    details = resp.get_json()["details"]
    assert any(d["field"] == "ticker" and d["type"] == "missing" for d in details)

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_monte_carlo_backend_error(mock_ub, client):
    instance = MagicMock()
    instance.run_monte_carlo.return_value = {"error": "Sim Failed"}
    mock_ub.return_value = instance

    resp = client.post("/analyze/monte-carlo", json={"ticker": "AAPL"})
    assert resp.status_code == 400
    assert "Sim Failed" in resp.get_json()["error"]

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_monte_carlo_exception(mock_ub, client):
    mock_ub.side_effect = Exception("Crash")
    resp = client.post("/analyze/monte-carlo", json={"ticker": "AAPL"})
    assert resp.status_code == 500

@patch('option_auditor.main_analyzer.fetch_live_prices')
def test_analyze_risk_profile_coverage(mock_fetch, client):
    # 1. Test Data Integrity Check ( > 20% Missing )
    manual_trades = [
        {"date": "2023-01-01", "symbol": "AAPL", "action": "BTO", "qty": 1, "price": 100, "fees": 1},
        {"date": "2023-01-01", "symbol": "GOOG", "action": "BTO", "qty": 1, "price": 100, "fees": 1},
        {"date": "2023-01-01", "symbol": "MSFT", "action": "BTO", "qty": 1, "price": 100, "fees": 1},
        {"date": "2023-01-01", "symbol": "AMZN", "action": "BTO", "qty": 1, "price": 100, "fees": 1},
        {"date": "2023-01-01", "symbol": "TSLA", "action": "BTO", "qty": 1, "price": 100, "fees": 1},
    ]

    # Mock fetch_live_prices to return only 3 prices (AAPL, GOOG, MSFT)
    # AMZN, TSLA missing -> 2/5 = 40% missing -> Alert
    mock_fetch.return_value = {
        "AAPL": 150.0,
        "GOOG": 150.0,
        "MSFT": 150.0
    }

    data = {
        "manual_trades": json.dumps(manual_trades),
        "risk_profile": json.dumps({"max_fee_drag": 5.0}),
        "broker": "manual"
    }

    resp = client.post("/analyze", data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    res_json = resp.get_json()

    assert "Data Integrity Failure" in res_json["verdict"]
    assert "red" in res_json["verdict_color"]
    assert "Critical" in res_json["verdict_details"]

    # 2. Test Fee Drag Alert
    # Create a completed trade with high fees
    # Buy 1 share @ 100, Sell @ 110. Profit = 10.
    # Fees = 20. Drag = 200%.
    manual_trades_2 = [
         {"date": "2023-01-01", "symbol": "IBM", "action": "BTO", "qty": 1, "price": 100, "fees": 10},
         {"date": "2023-01-02", "symbol": "IBM", "action": "STC", "qty": 1, "price": 110, "fees": 10},
    ]

    data_2 = {
        "manual_trades": json.dumps(manual_trades_2),
        "risk_profile": json.dumps({"max_fee_drag": 5.0}),
        "broker": "manual"
    }

    # We need to ensure mock returns something to avoid Data Integrity error here
    # 1 symbol IBM. If missing -> 100% fail.
    mock_fetch.return_value = {"IBM": 120.0}

    resp_2 = client.post("/analyze", data=data_2, content_type='multipart/form-data')
    assert resp_2.status_code == 200
    res_2 = resp_2.get_json()

    assert "broker_alert" in res_2
    assert "Fee Drag Exceeds User Limit" in res_2["broker_alert"]
