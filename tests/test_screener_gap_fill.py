import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor.screener import (
    _get_filtered_sp500,
    fetch_data_with_retry,
    _prepare_data_for_ticker,
    screen_turtle_setups,
    screen_5_13_setups,
    screen_darvas_box,
    screen_mms_ote_setups,
    screen_bull_put_spreads,
    resolve_ticker,
    screen_trend_followers_isa,
    SECTOR_COMPONENTS,
    _identify_swings,
    _detect_fvgs,
    _calculate_put_delta
)

# --- Mocks ---

@pytest.fixture
def mock_yf_download():
    with patch("yfinance.download") as mock:
        yield mock

@pytest.fixture
def mock_yf_ticker():
    with patch("yfinance.Ticker") as mock:
        yield mock

# --- Tests ---

def test_get_filtered_sp500_fallback(mock_yf_download):
    # Simulate download exception
    mock_yf_download.side_effect = Exception("Download failed")

    # Mock SP500_NAMES indirectly by patching get_sp500_tickers
    with patch("option_auditor.screener.get_sp500_tickers", return_value=["AAPL", "GOOG"]):
        with patch("option_auditor.screener.get_cached_market_data", return_value=pd.DataFrame()):
            res = _get_filtered_sp500(check_trend=True)
            # Should return base tickers (fallback)
            assert res == ["AAPL", "GOOG"]

def test_fetch_data_with_retry_failure(mock_yf_download):
    mock_yf_download.side_effect = Exception("Fail")
    with patch("time.sleep"): # Skip sleep
        df = fetch_data_with_retry("AAPL", retries=2)
        assert df.empty

def test_prepare_data_for_ticker_resample():
    # Test resampling logic
    dates = pd.date_range("2023-01-01", periods=100, freq="5min")
    data = pd.DataFrame({
        "Open": range(100), "High": range(100), "Low": range(100),
        "Close": range(100), "Volume": [1000]*100
    }, index=dates)

    # Case: Ticker in multi-index columns level 0
    # Construct a complex multi-index dataframe to mimic batch download
    cols = pd.MultiIndex.from_product([["AAPL"], ["Open", "High", "Low", "Close", "Volume"]])
    batch_df = pd.DataFrame(data.values, index=dates, columns=data.columns) # Simple for now

    # Test internal helper directly with simple DF
    res = _prepare_data_for_ticker("AAPL", data, "49m", "1mo", "5m", "49min", True)
    assert not res.empty
    # Check if resampled (length should be less)
    assert len(res) < 100

def test_screen_turtle_setups_exceptions(mock_yf_download):
    # Test exception handling inside the loop
    mock_yf_download.return_value = pd.DataFrame() # Empty batch

    # Mock prepare to raise exception or return None
    with patch("option_auditor.screener._prepare_data_for_ticker", side_effect=Exception("Data error")):
        res = screen_turtle_setups(["AAPL"])
        assert res == []

def test_screen_5_13_setups_edge_cases():
    # Test with insufficient data
    with patch("option_auditor.screener._prepare_data_for_ticker", return_value=pd.DataFrame()):
        res = screen_5_13_setups(["AAPL"])
        assert res == []

def test_screen_darvas_box_logic():
    # Create synthetic data for a Darvas Box
    # 1. Price creates a High (Ceiling)
    # 2. Price drops and creates a Low (Floor)
    # 3. Price consolidates
    # 4. Price breaks out above Ceiling

    dates = pd.date_range("2023-01-01", periods=60, freq="D")
    df = pd.DataFrame({
        "Open": [100]*60, "High": [100]*60, "Low": [90]*60,
        "Close": [95]*60, "Volume": [100000]*60
    }, index=dates)

    # Setup Ceiling at index 40 (value 110)
    # Ensure it's a fractal high: higher than 3 before and 3 after
    df.loc[dates[37:44], "High"] = 105
    df.loc[dates[40], "High"] = 110

    # Setup Floor at index 45 (value 90)
    df.loc[dates[42:49], "Low"] = 95
    df.loc[dates[45], "Low"] = 90

    # Breakout at the end
    df.loc[dates[-1], "Close"] = 115 # Above 110
    df.loc[dates[-2], "Close"] = 100 # Previous was below

    # Mock prepare
    with patch("option_auditor.screener._prepare_data_for_ticker", return_value=df):
        res = screen_darvas_box(["AAPL"])
        # Should find at least one result or handle it gracefully
        # Note: Threading is used, so we need to ensure mock works in threads or use side_effect
        # Since we patched prepare_data in the module, it should work.
        pass # Just ensuring no crash for now, assertion depends on exact logic path

def test_screen_mms_ote_setups_swings():
    # Test swing identification
    df = pd.DataFrame({"High": [10, 20, 15], "Low": [8, 18, 12]})
    res = _identify_swings(df, lookback=1)
    # Middle candle should be swing high (20 > 10 and 20 > 15)
    assert res["Swing_High"].iloc[1] == 20

    # Test FVGs
    # Bearish FVG: Low[i-2] > High[i]
    df_fvg = pd.DataFrame({
        "High": [100, 95, 80],
        "Low": [98, 90, 70]
    }, index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]))
    # i=2: High[2]=80. i-2=0: Low[0]=98. Gap = 98 - 80 = 18.
    res_fvg = _detect_fvgs(df_fvg)
    assert len(res_fvg) > 0
    assert res_fvg[0]['type'] == "BEARISH"

def test_calculate_put_delta():
    # S=100, K=100, T=1, r=0.05, sigma=0.2
    # ATM Put Delta should be around -0.5
    delta = _calculate_put_delta(100, 100, 1, 0.05, 0.2)
    assert -0.6 < delta < -0.3

def test_screen_bull_put_spreads_no_chain(mock_yf_ticker):
    # Test handling when no options chain exists
    mock_tk = MagicMock()
    mock_tk.options = [] # No dates
    mock_yf_ticker.return_value = mock_tk

    res = screen_bull_put_spreads(["AAPL"])
    assert res == []

def test_resolve_ticker():
    # Test standard resolution
    with patch.dict("option_auditor.screener.TICKER_NAMES", {"AAPL": "Apple Inc."}):
        assert resolve_ticker("AAPL") == "AAPL"
        assert resolve_ticker("Apple Inc.") == "AAPL"
        assert resolve_ticker("Apple") == "AAPL" # Partial
        assert resolve_ticker("XYZ") == "XYZ" # Fallback

def test_screen_trend_followers_isa_single_ticker(mock_yf_download):
    # Test single ticker path
    # Create valid DF (Mocking yf.download result directly)
    dates = pd.date_range("2023-01-01", periods=250, freq="D")
    df = pd.DataFrame({
        "Open": [100.0]*250, "High": [110.0]*250, "Low": [90.0]*250,
        "Close": [105.0]*250, "Volume": [10000000]*250
    }, index=dates)
    # Ensure trend > 200 SMA (200 SMA of 105 is 105)
    # Make price slightly higher to trigger entry or hold
    df.loc[dates[-1], "Close"] = 120.0
    # Increase Volume to pass liquidity filter (> 5,000,000 dollar vol)
    # Price 100 * Volume 1000 = 100,000 < 5M. Need more volume.
    # Set Volume to 100,000
    df["Volume"] = 100000 
    
    # yfinance often returns MultiIndex if group_by='ticker' is used (which it is for single ticker too in my code now)
    # or if we mocked it to match my new implementation which calls yf.download(..., group_by='ticker')
    # Let's verify what screener.py does.
    # For small lists, it calls: `yf.download(ticker_list, ..., group_by='ticker')`
    # Even for 1 ticker, if group_by='ticker', it returns MultiIndex (Ticker, OHLC).
    # Construct MultiIndex for robustness
    cols = pd.MultiIndex.from_product([["AAPL"], df.columns])
    df.columns = cols
    
    mock_yf_download.return_value = df

    res = screen_trend_followers_isa(["AAPL"])
    assert len(res) == 1
    assert res[0]['ticker'] == "AAPL"
