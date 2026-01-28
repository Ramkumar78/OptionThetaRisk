import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from option_auditor import screener

@pytest.fixture
def mock_yf_download():
    with patch('yfinance.download') as mock:
        yield mock

def create_mock_df(closes, volume=1000000):
    # Create a DataFrame with enough rows
    dates = pd.date_range(end=pd.Timestamp.now(), periods=len(closes))
    df = pd.DataFrame({
        'Open': closes,
        'High': [c * 1.01 for c in closes],
        'Low': [c * 0.99 for c in closes],
        'Close': closes,
        'Volume': [volume] * len(closes)
    }, index=dates)
    return df

def test_hybrid_volume_filtering(mock_yf_download):
    # Setup tickers
    # T1: Liquid (>500k vol) -> Should Pass
    # T2: Illiquid (<500k vol) -> Should be Filtered
    # T3: Watch List Illiquid -> Should Pass (Bypass filter)

    tickers = ["LIQUID", "ILLIQUID", "WATCH_ILLIQUID"]

    # Mock Data
    # 200 days required
    closes = [100.0] * 250

    # Create mocked batch download result
    # yfinance returns MultiIndex if group_by='ticker'
    # Columns: (Ticker, OHLCV)

    # Liquid
    df_liq = create_mock_df(closes, volume=1000000)
    # Illiquid
    df_ill = create_mock_df(closes, volume=100000)
    # Watch Illiquid
    df_watch = create_mock_df(closes, volume=100000)

    # Combine into MultiIndex DataFrame
    frames = {
        "LIQUID": df_liq,
        "ILLIQUID": df_ill,
        "WATCH_ILLIQUID": df_watch
    }

    # Construct MultiIndex columns
    # We need to concat properly
    dfs = []
    keys = []
    for k, v in frames.items():
        dfs.append(v)
        keys.append(k)

    batch_df = pd.concat(dfs, axis=1, keys=keys)

    mock_yf_download.return_value = batch_df

    # Patch SECTOR_COMPONENTS["WATCH"]
    with patch.dict(screener.SECTOR_COMPONENTS, {"WATCH": ["WATCH_ILLIQUID"]}):
        results = screener.screen_hybrid_strategy(ticker_list=tickers, time_frame="1d")

    result_tickers = [r['ticker'] for r in results]

    # Debug info
    print(f"Results: {result_tickers}")

    assert "LIQUID" in result_tickers
    assert "ILLIQUID" not in result_tickers
    assert "WATCH_ILLIQUID" in result_tickers
