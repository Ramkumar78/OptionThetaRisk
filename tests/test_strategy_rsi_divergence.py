import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from option_auditor.strategies.rsi_divergence import RsiDivergenceStrategy

@pytest.fixture
def mock_df():
    dates = pd.date_range(start="2023-01-01", periods=100)
    data = {
        'Open': np.ones(100) * 100,
        'High': np.ones(100) * 100,
        'Low': np.ones(100) * 100,
        'Close': np.ones(100) * 100,
        'Volume': np.ones(100) * 1000000
    }
    return pd.DataFrame(data, index=dates)

def test_bullish_divergence(mock_df):
    # Setup Price: Lower Low
    # indices: 80 and 95 (near end, within lookback)

    # Reset Close to 100
    mock_df['Close'] = 100.0

    col_idx = mock_df.columns.get_loc('Close')

    # Create Low 1 at idx 80
    mock_df.iloc[79, col_idx] = 102
    mock_df.iloc[80, col_idx] = 90
    mock_df.iloc[81, col_idx] = 102

    # Create Low 2 at idx 95 (Lower than Low 1)
    mock_df.iloc[94, col_idx] = 102
    mock_df.iloc[95, col_idx] = 85
    mock_df.iloc[96, col_idx] = 102

    # Setup RSI: Higher Low
    rsi_series = pd.Series(np.ones(100) * 50, index=mock_df.index)
    rsi_series.iloc[80] = 30 # Low 1 (Oversold)
    rsi_series.iloc[95] = 40 # Low 2 (Higher)

    # We mock pandas_ta.rsi and pandas_ta.atr
    with patch('option_auditor.strategies.rsi_divergence.ta.rsi', return_value=rsi_series):
        with patch('option_auditor.strategies.rsi_divergence.ta.atr', return_value=pd.Series(np.ones(100)*2, index=mock_df.index)):
            strategy = RsiDivergenceStrategy("TEST", mock_df)
            result = strategy.analyze()

            assert result is not None
            assert "BULLISH DIVERGENCE" in result['signal']
            # Stop loss for Bullish is BELOW price
            assert result['stop_loss'] < result['price']

def test_bearish_divergence(mock_df):
    # Setup Price: Higher High
    mock_df['Close'] = 100.0

    col_idx = mock_df.columns.get_loc('Close')

    # High 1 at idx 80
    mock_df.iloc[79, col_idx] = 98
    mock_df.iloc[80, col_idx] = 110
    mock_df.iloc[81, col_idx] = 98

    # High 2 at idx 95 (Higher than High 1)
    mock_df.iloc[94, col_idx] = 98
    mock_df.iloc[95, col_idx] = 115
    mock_df.iloc[96, col_idx] = 98

    # Setup RSI: Lower High
    rsi_series = pd.Series(np.ones(100) * 50, index=mock_df.index)
    rsi_series.iloc[80] = 70 # High 1
    rsi_series.iloc[95] = 60 # High 2 (Lower)

    with patch('option_auditor.strategies.rsi_divergence.ta.rsi', return_value=rsi_series):
        with patch('option_auditor.strategies.rsi_divergence.ta.atr', return_value=pd.Series(np.ones(100)*2, index=mock_df.index)):
            strategy = RsiDivergenceStrategy("TEST", mock_df)
            result = strategy.analyze()

            assert result is not None
            assert "BEARISH DIVERGENCE" in result['signal']
            # Stop loss for Bearish is ABOVE price
            assert result['stop_loss'] > result['price']
