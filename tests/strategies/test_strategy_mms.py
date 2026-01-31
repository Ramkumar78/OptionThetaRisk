import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from option_auditor.strategies.mms_ote import screen_mms_ote_setups

# Helper to create OTE setup data
def create_ote_data(days=100, pattern="bearish"):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days)
    data = {
        'Open': np.full(days, 100.0),
        'High': np.full(days, 100.0),
        'Low': np.full(days, 100.0),
        'Close': np.full(days, 100.0),
        'Volume': np.full(days, 1000000)
    }
    df = pd.DataFrame(data, index=dates)

    if pattern == "bearish":
        # 1. Structural Low (before peak)
        df.iloc[-50, df.columns.get_loc('Low')] = 90.0
        # 2. Peak High
        df.iloc[-40, df.columns.get_loc('High')] = 120.0
        # 3. Valley Low (MSS: Lower than Structural Low)
        df.iloc[-30, df.columns.get_loc('Low')] = 85.0

        # Range = 120 - 85 = 35
        # 62% Retrace = 120 - (35 * 0.618) = 98.37
        # 79% Retrace = 120 - (35 * 0.79) = 92.35

        # 4. Bearish FVG
        idx_fvg = -20
        df.iloc[idx_fvg-1, df.columns.get_loc('Low')] = 115.0 # i-1
        df.iloc[idx_fvg, df.columns.get_loc('Open')] = 114.0 # i
        df.iloc[idx_fvg, df.columns.get_loc('Close')] = 105.0
        df.iloc[idx_fvg, df.columns.get_loc('High')] = 114.0
        df.iloc[idx_fvg, df.columns.get_loc('Low')] = 105.0
        df.iloc[idx_fvg+1, df.columns.get_loc('High')] = 104.0 # i+1

        # 5. Current Price in OTE Zone (92.35 - 98.37)
        df.iloc[-1, df.columns.get_loc('Close')] = 95.0
        df.iloc[-1, df.columns.get_loc('High')] = 96.0
        df.iloc[-1, df.columns.get_loc('Low')] = 94.0

    if pattern == "bullish":
        # 1. Structural High (before trough) to create MSS
        df.iloc[-50, df.columns.get_loc('High')] = 110.0
        # 2. Trough Low
        df.iloc[-40, df.columns.get_loc('Low')] = 80.0
        # 3. Peak Up (MSS: Higher than Structural High)
        df.iloc[-30, df.columns.get_loc('High')] = 120.0

        # Range = 120 - 80 = 40
        # 62% Retrace Down = 80 + (40 * 0.618) = 104.72
        # 79% Retrace Down = 80 + (40 * 0.79) = 111.6 (Note: Logic is typically 1 - pct for pullback from peak?)
        # Logic in code: fib_62_up = trough_low + (range_up * 0.618) ... retracement_pct = (peak - curr) / range
        # Retracement 0.618 means we pulled back 61.8% FROM THE PEAK down to Trough.
        # Price = Peak - (Range * 0.618) = 120 - 24.72 = 95.28
        # Price = Peak - (Range * 0.79) = 120 - 31.6 = 88.4

        # 4. Current Price in OTE Zone (88.4 - 95.28)
        df.iloc[-1, df.columns.get_loc('Close')] = 90.0
        df.iloc[-1, df.columns.get_loc('High')] = 91.0
        df.iloc[-1, df.columns.get_loc('Low')] = 89.0

        # Ensure swings are detected (Need lower highs/lows around peaks/troughs)
        # The flat initialization with 100 might interfere if we don't set surrounding points.
        # Trough at -40 (80). Surrounding should be > 80.
        df.iloc[-41, df.columns.get_loc('Low')] = 90.0
        df.iloc[-39, df.columns.get_loc('Low')] = 90.0
        # Peak at -30 (120). Surrounding < 120.
        df.iloc[-31, df.columns.get_loc('High')] = 110.0
        df.iloc[-29, df.columns.get_loc('High')] = 110.0

    if pattern == "flat":
        # Create a simple steady uptrend that shouldn't trigger OTE (requires deep retracement)
        # Price goes 100 -> 110 steadily
        df['Close'] = np.linspace(100, 110, days)
        df['High'] = df['Close'] + 0.5
        df['Low'] = df['Close'] - 0.5
        df['Open'] = df['Close']

    return df

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_bullish_setup(mock_fetch):
    df = create_ote_data(days=100, pattern="bullish")
    mock_fetch.return_value = df

    results = screen_mms_ote_setups(ticker_list=["OTE_BULL"], check_mode=True)

    assert len(results) == 1
    assert "BULLISH OTE" in results[0]['signal']

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_bearish_setup(mock_fetch):
    df = create_ote_data(days=100, pattern="bearish")
    mock_fetch.return_value = df

    results = screen_mms_ote_setups(ticker_list=["OTE_BEAR"], check_mode=True)

    assert len(results) == 1
    assert 'signal' in results[0]
    # It should find the bearish OTE
    assert "BEARISH OTE" in results[0]['signal']

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_no_setup(mock_fetch):
    df = create_ote_data(days=100, pattern="flat")
    mock_fetch.return_value = df
    results = screen_mms_ote_setups(ticker_list=["FLAT"], check_mode=True)

    if results:
        assert results[0]['signal'] == "WAIT"
    else:
        assert len(results) == 0
