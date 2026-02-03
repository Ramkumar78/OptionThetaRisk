import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.strategies.monte_carlo import screen_monte_carlo_forecast

@patch('yfinance.download')
def test_monte_carlo_forecast_success(mock_download):
    # Mock data with sufficient history
    dates = pd.date_range("2021-01-01", "2023-01-01", freq="B")
    data = pd.DataFrame({
        "Close": np.linspace(100, 200, len(dates)) + np.random.normal(0, 5, len(dates)),
        "Open": np.linspace(100, 200, len(dates)),
        "High": np.linspace(100, 200, len(dates)),
        "Low": np.linspace(100, 200, len(dates)),
        "Volume": [1000] * len(dates)
    }, index=dates)

    mock_download.return_value = data

    result = screen_monte_carlo_forecast("AAPL")

    assert result is not None
    assert result["ticker"] == "AAPL"
    assert "median_forecast" in result
    assert "prob_drop_10pct" in result
    assert "volatility_annual" in result

@patch('yfinance.download')
def test_monte_carlo_forecast_insufficient_data(mock_download):
    dates = pd.date_range("2023-01-01", "2023-02-01", freq="B")
    data = pd.DataFrame({
        "Close": np.random.randn(len(dates))
    }, index=dates)

    mock_download.return_value = data

    result = screen_monte_carlo_forecast("AAPL")

    assert result is None

@patch('yfinance.download')
def test_monte_carlo_forecast_empty_data(mock_download):
    mock_download.return_value = pd.DataFrame()

    result = screen_monte_carlo_forecast("AAPL")

    assert result is None

@patch('yfinance.download')
def test_monte_carlo_forecast_multiindex(mock_download):
    # Mock MultiIndex data (e.g. from yfinance with multiple tickers or just one)
    dates = pd.date_range("2021-01-01", "2023-01-01", freq="B")

    # Create MultiIndex columns
    mi = pd.MultiIndex.from_product([["AAPL"], ["Close", "Open", "High", "Low", "Volume"]])

    data = pd.DataFrame(
        np.random.randn(len(dates), 5),
        index=dates,
        columns=mi
    )
    # Ensure Close is positive
    data[("AAPL", "Close")] = np.linspace(100, 200, len(dates))

    mock_download.return_value = data

    result = screen_monte_carlo_forecast("AAPL")

    assert result is not None
    assert result["ticker"] == "AAPL"
