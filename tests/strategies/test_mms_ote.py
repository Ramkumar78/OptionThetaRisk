import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.strategies.mms_ote import screen_mms_ote_setups

@pytest.fixture
def sample_ote_df():
    # Construct a DF that triggers OTE?
    # Or just generic one to ensure it runs without error.
    dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
    data = {
        'Open': np.linspace(100, 110, 100),
        'High': np.linspace(101, 111, 100),
        'Low': np.linspace(99, 109, 100),
        'Close': np.linspace(100, 110, 100),
        'Volume': [1000] * 100
    }
    return pd.DataFrame(data, index=dates)

@patch('option_auditor.strategies.mms_ote.ScreeningRunner')
@patch('option_auditor.strategies.mms_ote._identify_swings')
@patch('option_auditor.strategies.mms_ote._detect_fvgs')
def test_screen_mms_ote_setups(mock_detect_fvgs, mock_identify_swings, mock_runner_cls, sample_ote_df):
    mock_runner = mock_runner_cls.return_value

    # Mock helpers
    mock_identify_swings.return_value = sample_ote_df.copy()
    # Add dummy swing columns
    mock_identify_swings.return_value['Swing_High'] = np.nan
    mock_identify_swings.return_value['Swing_Low'] = np.nan
    # Set a swing
    mock_identify_swings.return_value.iloc[50, mock_identify_swings.return_value.columns.get_loc('Swing_High')] = 105.0
    mock_identify_swings.return_value.iloc[60, mock_identify_swings.return_value.columns.get_loc('Swing_Low')] = 100.0

    mock_detect_fvgs.return_value = [{'type': 'BEARISH'}]

    def side_effect_run(strategy_func):
        res = strategy_func('AAPL', sample_ote_df)
        return [res] if res else []

    mock_runner.run.side_effect = side_effect_run

    results = screen_mms_ote_setups(ticker_list=['AAPL'])

    # Even if logic doesn't trigger a buy/sell, it should run without error
    # With generic data, it likely returns None or runs through
    # If it returns None, results is empty list.

    assert isinstance(results, list)
