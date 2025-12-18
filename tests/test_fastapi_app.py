from fastapi.testclient import TestClient
from webapp.main import fastapi_app
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd

client = TestClient(fastapi_app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == "OK"

@patch("webapp.main.async_fetch_data_with_retry", new_callable=AsyncMock)
@patch("option_auditor.strategies.isa.IsaStrategy.analyze")
@patch("option_auditor.screener.resolve_ticker")
def test_check_isa_stock_success(mock_resolve, mock_analyze, mock_fetch):
    mock_resolve.return_value = "AAPL"

    # Create a real DataFrame to ensure all pandas operations work
    df_real = pd.DataFrame({'Close': [100.0] * 200 + [150.0]})
    mock_fetch.return_value = df_real

    mock_analyze.return_value = {
        "signal": "ENTER LONG",
        "trailing_exit_20d": 140.0
    }

    response = client.get("/api/screen/isa/check?ticker=AAPL&entry_price=145.0")

    # If this fails, print the error details
    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["details"]["pnl_value"] == 5.0
    assert "HOLD" in data["signal"]

@patch("webapp.main.async_fetch_data_with_retry", new_callable=AsyncMock)
@patch("option_auditor.screener.resolve_ticker")
def test_check_isa_stock_no_data(mock_resolve, mock_fetch):
    mock_resolve.return_value = "INVALID"
    mock_fetch.return_value = pd.DataFrame() # Empty

    response = client.get("/api/screen/isa/check?ticker=INVALID")

    if response.status_code != 404:
        print(response.json())

    assert response.status_code == 404
