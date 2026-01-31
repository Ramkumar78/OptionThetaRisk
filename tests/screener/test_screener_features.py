import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_5_13_setups, screen_turtle_setups

@pytest.fixture
def mock_yf_download():
    with patch('yfinance.download') as mock:
        yield mock

def create_mock_df(periods=50, close_pattern="up"):
    """Creates a mock DataFrame for yfinance."""
    dates = pd.date_range(start="2023-01-01", periods=periods, freq="B")

    if close_pattern == "up":
        # Trending up
        close = np.linspace(100, 150, periods)
    elif close_pattern == "down":
        # Trending down
        close = np.linspace(150, 100, periods)
    elif close_pattern == "breakout_5_21":
        # Flat then spike to cross EMAs
        # EMA 21 ~ SMA 21 initially.
        # We need 5 EMA to cross 21 EMA.
        close = np.full(periods, 100.0)
        # Last few days spike up
        close[-3:] = [105, 110, 115]
    elif close_pattern == "darvas_breakout":
        # Box range 100-110 for 20 days, then 112
        close = np.random.uniform(100, 110, periods)
        high = close + 1
        low = close - 1
        # Make a high box for 15 days
        high[-20:-1] = 110 # Set highs
        # Today breakout
        close[-1] = 112
        high[-1] = 113

        df = pd.DataFrame({
            "Open": close, "High": high, "Low": low, "Close": close, "Volume": 1000
        }, index=dates)
        return df

    # Standard columns
    high = close * 1.01
    low = close * 0.99

    df = pd.DataFrame({
        "Open": close, "High": high, "Low": low, "Close": close, "Volume": 1000
    }, index=dates)
    return df

def test_screen_5_13_pct_change(mock_yf_download):
    """Test that pct_change_1d is calculated and returned."""
    mock_df = create_mock_df(periods=30, close_pattern="up")
    mock_yf_download.return_value = mock_df

    # We mock _prepare_data_for_ticker to just return our mock_df
    with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=mock_df):
        results = screen_5_13_setups(ticker_list=["AAPL"], time_frame="1d")

    assert len(results) == 1
    # Check pct change exists
    assert "pct_change_1d" in results[0]
    # Since it's linear up 100->150 over 30 days, change is positive
    assert results[0]["pct_change_1d"] > 0

def test_screen_5_13_priority_21(mock_yf_download):
    """Test that 5/21 breakout is prioritized."""
    # We construct a scenario where 5 crosses 21
    # We can mock pandas_ta.ema directly to control values

    mock_df = create_mock_df(periods=30)

    with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=mock_df), \
         patch('pandas_ta.ema') as mock_ema:

        # Setup EMA side effects
        # We need 3 calls: 5, 13, 21
        # We want to simulate:
        # Prev: 5 < 21 (and maybe 5 < 13)
        # Curr: 5 > 21 (Fresh Breakout)

        # Helper to create Series
        def make_series(val_prev, val_curr):
            s = pd.Series([0]*28 + [val_prev, val_curr], index=mock_df.index)
            return s

        # EMA 5: 100 -> 110
        ema_5 = make_series(100, 110)
        # EMA 13: 105 -> 106
        ema_13 = make_series(105, 106)
        # EMA 21: 108 -> 109
        ema_21 = make_series(108, 109)

        # mock_ema is called 3 times per ticker.
        # Order: 5, 13, 21
        mock_ema.side_effect = [ema_5, ema_13, ema_21]

        results = screen_5_13_setups(ticker_list=["AAPL"], time_frame="1d")

    assert len(results) == 1
    # Prev: 5(100) < 21(108)
    # Curr: 5(110) > 21(109)
    # This is a Fresh 5/21 Breakout
    assert "FRESH 5/21 BREAKOUT" in results[0]["signal"]

def test_screen_turtle_no_darvas_leakage(mock_yf_download):
    """Test that Turtle screener does NOT report Darvas (10-day) breakouts."""
    mock_df = create_mock_df(periods=30, close_pattern="darvas_breakout")

    dates = pd.date_range(start="2023-01-01", periods=30)
    # We construct specific arrays

    highs = [100.0] * 30
    highs[10] = 115.0 # Sets 20-day high to 115
    # Indexes 19..28 are all 100. So 10-day high is 100.

    close = [100.0] * 30
    close[-1] = 110.0 # Breakout of 10-day (100) but not 20-day (115)

    lows = [c * 0.9 for c in close]

    df = pd.DataFrame({"High": highs, "Low": lows, "Close": close, "Volume": 1000}, index=dates)

    # ATR mock
    with patch('option_auditor.common.screener_utils.prepare_data_for_ticker', return_value=df), \
         patch('pandas_ta.atr', return_value=pd.Series([1.0]*30, index=dates)):

         results = screen_turtle_setups(ticker_list=["AAPL"], time_frame="1d")

    # Should be empty because Turtle only cares about 20-day high (115)
    assert len(results) == 0
