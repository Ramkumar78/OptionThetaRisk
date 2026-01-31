import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.screener import screen_liquidity_grabs

def test_screen_liquidity_grabs_bullish_sweep():
    # Mock data with a bullish sweep pattern
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1h")
    data = pd.DataFrame(index=dates)
    data['Open'] = 100.0
    data['High'] = 105.0
    data['Low'] = 95.0
    data['Close'] = 100.0
    data['Volume'] = 1000000.0

    # Create a swing low at index 50
    # Swing Low needs to be lower than neighbors
    data.iloc[49, data.columns.get_loc('Low')] = 95.0
    data.iloc[50, data.columns.get_loc('Low')] = 90.0 # Swing Low
    data.iloc[51, data.columns.get_loc('Low')] = 95.0

    # Neighbors Highs to valid swing
    data.iloc[49, data.columns.get_loc('High')] = 100.0
    data.iloc[50, data.columns.get_loc('High')] = 100.0
    data.iloc[51, data.columns.get_loc('High')] = 100.0

    # Current candle (index -1) sweeps the low (90)
    # Low goes to 89, Close is 91 (Rejection)
    data.iloc[-1] = [95.0, 98.0, 89.0, 91.0, 2000000.0]

    with patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_fetch:
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker') as mock_prep:
            mock_prep.return_value = data

            results = screen_liquidity_grabs(["TEST"], time_frame="1h")

            assert len(results) == 1
            res = results[0]
            assert res['ticker'] == "TEST"
            assert "BULLISH SWEEP" in res['signal']
            assert res['breakout_level'] == 90.0
            assert res['price'] == 91.0

def test_screen_liquidity_grabs_bearish_sweep():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="1h")
    data = pd.DataFrame(index=dates)
    data['Open'] = 100.0
    data['High'] = 105.0
    data['Low'] = 95.0
    data['Close'] = 100.0
    data['Volume'] = 1000000.0

    # Swing High at 50 (High=110)
    data.iloc[49, data.columns.get_loc('High')] = 105.0
    data.iloc[50, data.columns.get_loc('High')] = 110.0 # Swing High
    data.iloc[51, data.columns.get_loc('High')] = 105.0

    # Current candle sweeps 110 (High=111) but closes below (109)
    data.iloc[-1] = [108.0, 111.0, 105.0, 109.0, 1000000.0]

    with patch('option_auditor.common.screener_utils.fetch_batch_data_safe') as mock_fetch:
        with patch('option_auditor.common.screener_utils.prepare_data_for_ticker') as mock_prep:
            mock_prep.return_value = data

            results = screen_liquidity_grabs(["TEST"], time_frame="1h")

            assert len(results) == 1
            assert "BEARISH SWEEP" in results[0]['signal']
            assert results[0]['breakout_level'] == 110.0
