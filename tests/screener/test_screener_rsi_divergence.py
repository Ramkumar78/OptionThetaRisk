import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_rsi_divergence

def create_mock_divergence_df(pattern="bearish"):
    """
    Creates a mock DataFrame with specific price/RSI patterns.
    """
    periods = 50
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="B")

    # Base arrays
    close = np.linspace(100, 100, periods) # Flat base

    # We need peaks at index A and B
    # Let's say index 30 and 45 (recent)
    idx_1 = 30
    idx_2 = 45

    if pattern == "bearish":
        # Price: HH
        close[idx_1] = 110
        close[idx_2] = 115

        # Intermediate to ensure they are peaks (local maxima)
        # Neighbors must be lower
        close[idx_1-1] = 105
        close[idx_1+1] = 105
        close[idx_2-1] = 110
        close[idx_2+1] = 110

    elif pattern == "bullish":
        # Price: LL
        close[idx_1] = 90
        close[idx_2] = 85

        # Intermediate to ensure they are valleys (local minima)
        # Neighbors must be higher
        close[idx_1-1] = 95
        close[idx_1+1] = 95
        close[idx_2-1] = 90
        close[idx_2+1] = 90

    df = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000
    }, index=dates)

    return df

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('pandas_ta.rsi')
@patch('pandas_ta.atr')
def test_screen_rsi_bearish_divergence(mock_atr, mock_rsi, mock_fetch):
    # Setup Data
    df = create_mock_divergence_df("bearish")
    mock_fetch.return_value = df

    # Setup RSI Mock
    # RSI: LH (Peak 1 > Peak 2)
    # Price was HH (110 -> 115)
    rsi_vals = np.linspace(50, 50, 50)
    rsi_vals[30] = 80 # Peak 1
    rsi_vals[45] = 70 # Peak 2 (Lower High)

    # Ensure intermediate points are lower to make them peaks
    rsi_vals[29] = 70
    rsi_vals[31] = 70
    rsi_vals[44] = 60
    rsi_vals[46] = 60

    mock_rsi.return_value = pd.Series(rsi_vals, index=df.index)
    mock_atr.return_value = pd.Series(np.ones(50), index=df.index) # Mock ATR

    results = screen_rsi_divergence(ticker_list=["AAPL"], time_frame="1d")

    assert len(results) == 1
    assert results[0]['signal'] == "🐻 BEARISH DIVERGENCE"
    assert results[0]['ticker'] == "AAPL"

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('pandas_ta.rsi')
@patch('pandas_ta.atr')
def test_screen_rsi_bullish_divergence(mock_atr, mock_rsi, mock_fetch):
    # Setup Data
    df = create_mock_divergence_df("bullish")
    mock_fetch.return_value = df

    # Setup RSI Mock
    # Price: LL (90 -> 85)
    # RSI: HL (30 -> 40)
    rsi_vals = np.linspace(50, 50, 50)
    rsi_vals[30] = 30 # Low 1
    rsi_vals[45] = 40 # Low 2 (Higher Low)

    # Ensure intermediate points are higher to make them valleys
    rsi_vals[29] = 40
    rsi_vals[31] = 40
    rsi_vals[44] = 50
    rsi_vals[46] = 50

    mock_rsi.return_value = pd.Series(rsi_vals, index=df.index)
    mock_atr.return_value = pd.Series(np.ones(50), index=df.index)

    results = screen_rsi_divergence(ticker_list=["AAPL"], time_frame="1d")

    assert len(results) == 1
    assert results[0]['signal'] == "🐂 BULLISH DIVERGENCE"

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('pandas_ta.rsi')
def test_screen_rsi_no_divergence(mock_rsi, mock_fetch):
    # Convergence (Price HH, RSI HH)
    periods = 50
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="B")
    close = np.linspace(100, 100, periods)

    idx_1 = 30
    idx_2 = 45

    close[idx_1] = 110
    close[idx_2] = 115 # HH

    # Peaks
    close[idx_1-1]=105; close[idx_1+1]=105
    close[idx_2-1]=110; close[idx_2+1]=110

    df = pd.DataFrame({
        "Open": close, "High": close, "Low": close, "Close": close, "Volume": 1000
    }, index=dates)

    mock_fetch.return_value = df

    # RSI HH
    rsi_vals = np.linspace(50, 50, 50)
    rsi_vals[30] = 70
    rsi_vals[45] = 80 # HH

    rsi_vals[29]=60; rsi_vals[31]=60
    rsi_vals[44]=70; rsi_vals[46]=70

    mock_rsi.return_value = pd.Series(rsi_vals, index=df.index)

    results = screen_rsi_divergence(ticker_list=["AAPL"], time_frame="1d")

    assert len(results) == 0
