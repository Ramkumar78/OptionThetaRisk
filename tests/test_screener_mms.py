
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.screener import _identify_swings, _detect_fvgs, screen_mms_ote_setups

# --- Test Data Fixtures ---

@pytest.fixture
def sample_df():
    # Create a basic dataframe for testing
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    data = {
        "High": [10, 12, 11, 15, 13, 16, 14, 18, 17, 19],
        "Low":  [8,  9,  8,  12, 11, 13, 12, 15, 14, 16],
        "Close":[9, 11, 10, 14, 12, 15, 13, 17, 16, 18],
        "Volume": [1000] * 10
    }
    df = pd.DataFrame(data, index=dates)
    return df

@pytest.fixture
def bearish_ote_df():
    # Construct a Bearish OTE setup
    # 1. Swing High (Liquidity Pool)
    dates = pd.date_range(start="2023-01-01", periods=50, freq="h")
    highs = [110.0] * 50
    lows = [105.0] * 50
    closes = [108.0] * 50

    # Swing High at index 20
    highs[19] = 114
    highs[20] = 115 # Peak
    highs[21] = 113
    lows[19] = 112
    lows[20] = 113
    lows[21] = 111

    # Displacement Down at index 22
    highs[22] = 112
    lows[22] = 100 # Big drop
    closes[22] = 100

    # FVG creation (Gap between Low[20]=113 and High[22]=112? No.
    # Logic: Low[i-2] > High[i]. i=22. Low[20]=113 > High[22]=112. Gap=1. Yes.)

    # Valley Low at index 25
    lows[25] = 95 # Valley Low (Global Min)

    # Range High (115) - Low (95) = 20
    # Fib 62% retracement = 115 - (20 * 0.618) = 102.64
    # Fib 79% retracement = 115 - (20 * 0.79) = 99.20
    # OTE Zone: 99.20 to 102.64

    # Current Price (index 49) needs to be in Zone
    closes[49] = 100.0

    # MSS Structure Check
    # Need a Swing Low BEFORE the peak (index < 20) that is HIGHER than Valley (95).
    lows[14] = 99
    lows[15] = 98 # This is a swing low (99 > 98 < 99)
    lows[16] = 99
    # Valley (95) < Structure (98). MSS confirmed.

    df = pd.DataFrame({
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": [1000] * 50
    }, index=dates)

    return df

# --- Tests ---

def test_identify_swings(sample_df):
    # Highs: 10, 12, 11...
    # Index 1 (12) > 10 and 12 > 11. Should be Swing High.
    res = _identify_swings(sample_df)
    assert "Swing_High" in res.columns
    assert "Swing_Low" in res.columns

    # Check index 1
    assert not pd.isna(res['Swing_High'].iloc[1])
    assert res['Swing_High'].iloc[1] == 12

    # Check index 2 (11) is not swing high (12 > 11 < 15)
    assert pd.isna(res['Swing_High'].iloc[2])

def test_detect_fvgs():
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    # Bearish FVG setup
    # Candle 0: Low 105
    # Candle 1: Big red candle
    # Candle 2: High 100
    # Gap: 100 to 105 (size 5)

    df = pd.DataFrame({
        "High": [110, 108, 100, 95, 90],
        "Low":  [105, 100, 90, 85, 80],
        "Close":[108, 102, 95, 90, 85],
        "Volume": [100]*5
    }, index=dates)

    fvgs = _detect_fvgs(df)

    # Should find Bearish FVG at index 2 (looking back at 0)
    # Low[i-2] (105) > High[i] (100)
    assert len(fvgs) > 0
    fvg = fvgs[0]
    assert fvg['type'] == "BEARISH"
    assert fvg['top'] == 105
    assert fvg['bottom'] == 100

def test_screen_mms_ote_setup(bearish_ote_df):
    # Mock yfinance Ticker
    with patch('yfinance.Ticker') as MockTicker:
        instance = MockTicker.return_value
        instance.history.return_value = bearish_ote_df

        # Run screener
        results = screen_mms_ote_setups(ticker_list=["TEST"], time_frame="1h")

        assert len(results) == 1
        res = results[0]
        assert res['ticker'] == "TEST"
        assert "BEARISH OTE" in res['signal']
        assert res['fvg_detected'] == "Yes"

        # Verify OTE Zone calculation
        # Stop should be peak high (115)
        assert res['stop_loss'] == 115.0

def test_screen_mms_no_setup(sample_df):
    with patch('yfinance.Ticker') as MockTicker:
        instance = MockTicker.return_value
        instance.history.return_value = sample_df
        # This simple DF has no complex OTE structure
        results = screen_mms_ote_setups(ticker_list=["TEST"], time_frame="1h")
        assert len(results) == 0

def test_screen_mms_empty_data():
    with patch('yfinance.Ticker') as MockTicker:
        instance = MockTicker.return_value
        instance.history.return_value = pd.DataFrame()
        results = screen_mms_ote_setups(ticker_list=["TEST"], time_frame="1h")
        assert len(results) == 0
