import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.strategies.monte_carlo import screen_monte_carlo_forecast

@patch('option_auditor.strategies.monte_carlo.yf.download')
def test_screen_monte_carlo_forecast(mock_download):
    # Setup mock data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    # Use random walk to generate some returns
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    prices = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({'Close': prices}, index=dates)
    mock_download.return_value = df

    result = screen_monte_carlo_forecast('AAPL')

    assert result is not None
    assert result['ticker'] == 'AAPL'
    assert 'median_forecast' in result
    assert 'prob_drop_10pct' in result
    assert 'volatility_annual' in result
