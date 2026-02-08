import pytest
import json
import io
from unittest.mock import patch, MagicMock
from flask import g

# --- 1. Portfolio Analysis Tests ---

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_portfolio_risk')
def test_analyze_portfolio_success(mock_analyze, client):
    """Test /analyze/portfolio with valid input."""
    mock_analyze.return_value = {"risk_score": 50, "breakdown": {}}

    payload = {
        "positions": [
            {"symbol": "AAPL", "qty": 10, "entry_price": 150}
        ]
    }

    response = client.post('/analyze/portfolio', json=payload)

    assert response.status_code == 200
    assert response.json == {"risk_score": 50, "breakdown": {}}
    mock_analyze.assert_called_once()

def test_analyze_portfolio_invalid_input(client):
    """Test /analyze/portfolio with missing positions."""
    response = client.post('/analyze/portfolio', json={})
    assert response.status_code == 400
    assert "Validation Error" in response.json.get("error", "")

# --- 2. Portfolio Greeks Tests ---

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_portfolio_greeks')
def test_analyze_portfolio_greeks_success(mock_greeks, client):
    """Test /analyze/portfolio/greeks with valid input."""
    mock_greeks.return_value = {"delta": 100, "gamma": 0.5}

    payload = {
        "positions": [
            {"symbol": "AAPL", "qty": 100}
        ]
    }

    response = client.post('/analyze/portfolio/greeks', json=payload)

    assert response.status_code == 200
    assert response.json == {"delta": 100, "gamma": 0.5}

# --- 3. Scenario Analysis Tests ---

@patch('webapp.blueprints.analysis_routes.portfolio_risk.analyze_scenario')
def test_analyze_scenario_success(mock_scenario, client):
    """Test /analyze/scenario with valid input."""
    mock_scenario.return_value = {"pnl": -500}

    payload = {
        "positions": [{"symbol": "AAPL", "qty": 10}],
        "scenario": {"spot_change": -0.1, "vol_change": 0.2}
    }

    response = client.post('/analyze/scenario', json=payload)

    assert response.status_code == 200
    assert response.json == {"pnl": -500}

def test_analyze_scenario_missing_params(client):
    """Test /analyze/scenario with missing scenario data."""
    payload = {
        "positions": [{"symbol": "AAPL", "qty": 10}]
    }
    response = client.post('/analyze/scenario', json=payload)
    assert response.status_code == 400

# --- 4. Correlation Tests ---

@patch('webapp.blueprints.analysis_routes.calculate_correlation_matrix')
def test_analyze_correlation_success(mock_corr, client):
    """Test /analyze/correlation with valid input."""
    mock_corr.return_value = {
        "matrix": [[1.0, 0.5], [0.5, 1.0]],
        "tickers": ["AAPL", "MSFT"]
    }

    payload = {
        "tickers": ["AAPL", "MSFT"],
        "period": "1y"
    }

    response = client.post('/analyze/correlation', json=payload)

    assert response.status_code == 200
    assert response.json["tickers"] == ["AAPL", "MSFT"]

@patch('webapp.blueprints.analysis_routes.calculate_correlation_matrix')
def test_analyze_correlation_error(mock_corr, client):
    """Test /analyze/correlation when calculation fails."""
    mock_corr.return_value = {"error": "Insufficient data"}

    payload = {
        "tickers": ["UNKNOWN"],
        "period": "1y"
    }

    response = client.post('/analyze/correlation', json=payload)

    assert response.status_code == 400
    assert response.json == {"error": "Insufficient data"}

# --- 5. Backtest Tests ---

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_analyze_backtest_success(mock_ub_cls, client):
    """Test /analyze/backtest success."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = {"total_return": 0.15, "trades": 50}
    mock_ub_cls.return_value = mock_instance

    payload = {
        "ticker": "AAPL",
        "strategy": "master",
        "initial_capital": 20000
    }

    response = client.post('/analyze/backtest', json=payload)

    assert response.status_code == 200
    assert response.json["total_return"] == 0.15
    mock_ub_cls.assert_called_with("AAPL", strategy_type="master", initial_capital=20000)

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_analyze_backtest_failure(mock_ub_cls, client):
    """Test /analyze/backtest failure."""
    mock_instance = MagicMock()
    mock_instance.run.return_value = {"error": "Strategy execution failed"}
    mock_ub_cls.return_value = mock_instance

    payload = {"ticker": "AAPL"}

    response = client.post('/analyze/backtest', json=payload)

    assert response.status_code == 400
    assert response.json["error"] == "Strategy execution failed"

# --- 6. Monte Carlo Tests ---

@patch('webapp.blueprints.analysis_routes.UnifiedBacktester')
def test_analyze_monte_carlo_success(mock_ub_cls, client):
    """Test /analyze/monte-carlo success."""
    mock_instance = MagicMock()
    mock_instance.run_monte_carlo.return_value = {
        "simulation_results": [],
        "confidence_intervals": {}
    }
    mock_ub_cls.return_value = mock_instance

    payload = {
        "ticker": "AAPL",
        "strategy": "turtle",
        "simulations": 100
    }

    response = client.post('/analyze/monte-carlo', json=payload)

    assert response.status_code == 200
    assert "confidence_intervals" in response.json

# --- 7. Task Status Tests ---

@patch('webapp.blueprints.analysis_routes.AnalysisWorker')
def test_analyze_status_success(mock_worker_cls, client):
    """Test /analyze/status/<task_id> success."""
    mock_instance = MagicMock()
    mock_instance.get_result.return_value = {"status": "completed", "result": "done"}
    mock_worker_cls.instance.return_value = mock_instance

    response = client.get('/analyze/status/task-123')

    assert response.status_code == 200
    assert response.json["status"] == "completed"

@patch('webapp.blueprints.analysis_routes.AnalysisWorker')
def test_analyze_status_not_found(mock_worker_cls, client):
    """Test /analyze/status/<task_id> not found."""
    mock_instance = MagicMock()
    mock_instance.get_result.return_value = {"status": "not_found"}
    mock_worker_cls.instance.return_value = mock_instance

    response = client.get('/analyze/status/invalid-task')

    assert response.status_code == 404

# --- 8. Market Data Tests ---

@patch('webapp.blueprints.analysis_routes.serialize_ohlc_data')
@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_analyze_market_data_success(mock_fetch, mock_serialize, client):
    """Test /analyze/market-data success."""
    mock_df = MagicMock()
    mock_df.empty = False
    mock_fetch.return_value = mock_df

    mock_serialize.return_value = [{"time": "2023-01-01", "value": 100}]

    payload = {"ticker": "AAPL", "period": "1y"}
    response = client.post('/analyze/market-data', json=payload)

    assert response.status_code == 200
    assert len(response.json) == 1

@patch('webapp.blueprints.analysis_routes.fetch_batch_data_safe')
def test_analyze_market_data_empty(mock_fetch, client):
    """Test /analyze/market-data empty response."""
    mock_df = MagicMock()
    mock_df.empty = True
    mock_fetch.return_value = mock_df

    payload = {"ticker": "UNKNOWN", "period": "1y"}
    response = client.post('/analyze/market-data', json=payload)

    assert response.status_code == 404

# --- 9. Strategies List Tests ---

@patch('webapp.blueprints.analysis_routes.get_strategy')
def test_list_strategies(mock_get_strategy, client):
    """Test /analyze/strategies."""
    mock_strategy = MagicMock()
    mock_strategy.get_retail_explanation.return_value = "A great strategy."
    mock_get_strategy.return_value = mock_strategy

    response = client.get('/analyze/strategies')

    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) > 0
    assert "explanation" in response.json[0]

# --- 10. Main Analyze Route Tests ---

@patch('webapp.blueprints.analysis_routes._get_storage_provider')
@patch('webapp.blueprints.analysis_routes.analyze_csv')
def test_analyze_manual_trades_success(mock_analyze_csv, mock_storage, client):
    """Test /analyze with manual trades input."""
    mock_analyze_csv.return_value = {
        "portfolio_stats": {"net_liquidity": 10000},
        "excel_report": None
    }

    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    # Prepare form data
    manual_trades = [
        {"date": "2023-01-01", "symbol": "AAPL", "action": "BUY", "qty": 10, "price": 150}
    ]

    data = {
        "manual_trades": json.dumps(manual_trades),
        "broker": "manual",
        "risk_profile": json.dumps({"max_fee_drag": 1.5})
    }

    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert "portfolio_stats" in response.json
    mock_analyze_csv.assert_called_once()

    # Check args passed to analyze_csv
    args, kwargs = mock_analyze_csv.call_args
    assert kwargs['manual_data'] == manual_trades
    assert kwargs['max_fee_drag'] == 1.5

@patch('webapp.blueprints.analysis_routes._get_storage_provider')
@patch('webapp.blueprints.analysis_routes.analyze_csv')
def test_analyze_csv_upload_success(mock_analyze_csv, mock_storage, client):
    """Test /analyze with CSV file upload."""
    mock_analyze_csv.return_value = {
        "portfolio_stats": {"net_liquidity": 50000},
        "excel_report": io.BytesIO(b"fake excel content")
    }

    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    data = {
        "csv": (io.BytesIO(b"Date,Symbol,Action,Qty,Price\n2023-01-01,AAPL,BUY,10,150"), "trades.csv"),
        "broker": "tastyworks"
    }

    response = client.post('/analyze', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert "token" in response.json

    # Verify excel report was saved
    mock_storage_instance.save_report.assert_called_once()

def test_analyze_no_input(client):
    """Test /analyze with no file and no manual trades."""
    response = client.post('/analyze', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "No input data provided" in response.json["error"]

def test_analyze_invalid_file_type(client):
    """Test /analyze with invalid file extension."""
    data = {
        "csv": (io.BytesIO(b"content"), "trades.txt"), # .txt not allowed usually
        "broker": "tastyworks"
    }

    response = client.post('/analyze', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert "Invalid file type" in response.json["error"]

# --- 11. Download Tests ---

@patch('webapp.blueprints.analysis_routes._get_storage_provider')
def test_download_success(mock_storage, client):
    """Test /download/<token>/<filename> success."""
    mock_instance = MagicMock()
    mock_instance.get_report.return_value = b"file content"
    mock_storage.return_value = mock_instance

    response = client.get('/download/token123/report.xlsx')

    assert response.status_code == 200
    assert response.data == b"file content"
    assert response.headers["Content-Disposition"] == 'attachment; filename=report.xlsx'

@patch('webapp.blueprints.analysis_routes._get_storage_provider')
def test_download_not_found(mock_storage, client):
    """Test /download/<token>/<filename> not found."""
    mock_instance = MagicMock()
    mock_instance.get_report.return_value = None
    mock_storage.return_value = mock_instance

    response = client.get('/download/token123/missing.xlsx')

    assert response.status_code == 404
