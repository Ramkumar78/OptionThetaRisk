import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.strategies.alpha import screen_alpha_101, screen_my_strategy

@pytest.fixture
def sample_df():
    dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
    # Trend up for SMA 200 check
    data = {
        'Open': np.linspace(100, 200, 200),
        'High': np.linspace(101, 201, 200),
        'Low': np.linspace(99, 199, 200),
        'Close': np.linspace(100, 200, 200),
    }
    return pd.DataFrame(data, index=dates)

@patch('option_auditor.strategies.alpha.ScreeningRunner')
def test_screen_alpha_101(mock_runner_cls, sample_df):
    mock_runner = mock_runner_cls.return_value

    def side_effect_run(strategy_func):
        # Create a scenario where Alpha #101 is high
        # Close >> Open
        df = sample_df.copy()
        df.iloc[-1, df.columns.get_loc('Close')] = 210
        df.iloc[-1, df.columns.get_loc('Open')] = 200
        df.iloc[-1, df.columns.get_loc('High')] = 210
        df.iloc[-1, df.columns.get_loc('Low')] = 200
        # Alpha = (210-200) / (10 + 0.001) ~ 1.0 > 0.5

        res = strategy_func('AAPL', df)
        return [res] if res else []

    mock_runner.run.side_effect = side_effect_run

    results = screen_alpha_101(['AAPL'])
    assert len(results) == 1
    assert results[0]['alpha_101'] > 0.5

@patch('option_auditor.strategies.alpha.ScreeningRunner')
def test_screen_my_strategy(mock_runner_cls, sample_df):
    mock_runner = mock_runner_cls.return_value

    def side_effect_run(strategy_func):
        # Need > 200 SMA (sample_df is rising, so Close > SMA)
        # Need Alpha > 0.5
        df = sample_df.copy()
        df.iloc[-1, df.columns.get_loc('Close')] = 210
        df.iloc[-1, df.columns.get_loc('Open')] = 200
        df.iloc[-1, df.columns.get_loc('High')] = 210
        df.iloc[-1, df.columns.get_loc('Low')] = 200

        res = strategy_func('AAPL', df)
        return [res] if res else []

    mock_runner.run.side_effect = side_effect_run

    results = screen_my_strategy(['AAPL'])
    assert len(results) == 1
    assert "SNIPER ENTRY" in results[0]['signal']
