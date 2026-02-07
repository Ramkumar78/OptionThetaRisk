import pytest
import pandas as pd
import numpy as np
from option_auditor.strategies.medallion_isa import MedallionIsaStrategy

def create_mock_df(trend="UP", rsi_mode="LOW", vol_mode="HIGH"):
    dates = pd.date_range(start="2023-01-01", periods=250)

    # Base Price
    if trend == "UP":
        # Strong uptrend: 100 to 500 (Steeper to keep Price > SMA50 during dip)
        close = np.linspace(100, 500, 250)
    else:
        # Downtrend: 200 to 100
        close = np.linspace(200, 100, 250)

    # Apply Volatility for ATR
    high = close + 2
    low = close - 2

    # Volume
    volume = np.full(250, 1000000)

    if vol_mode == "HIGH":
        volume[-1] = 2000000 # 2x Spike
    else:
        volume[-1] = 1000000 # Normal

    df = pd.DataFrame({
        "Open": close,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume
    }, index=dates)

    # Manipulate for RSI
    if rsi_mode == "LOW":
        # Sharp drop in last 3 days to tank RSI(3)
        # With 100->500 trend, SMA50 is ~460, Close is 500.
        # We need drops that keep Price > 460.
        # 1% drop per day for 3 days = ~485. Safe.

        df.iloc[-3, df.columns.get_loc('Close')] = df.iloc[-4]['Close'] * 0.99
        df.iloc[-2, df.columns.get_loc('Close')] = df.iloc[-3]['Close'] * 0.99
        df.iloc[-1, df.columns.get_loc('Close')] = df.iloc[-2]['Close'] * 0.99

        # Recalc high/low for these to be valid candles
        df.iloc[-3:, df.columns.get_loc('High')] = df.iloc[-3:]['Close'] + 1
        df.iloc[-3:, df.columns.get_loc('Low')] = df.iloc[-3:]['Close'] - 1

    return df

def test_medallion_isa_buy_signal():
    # Uptrend, Low RSI, High Vol
    df = create_mock_df(trend="UP", rsi_mode="LOW", vol_mode="HIGH")

    # We might need to tweak prices to ensure SMA50 < Close
    # With linear growth, SMA50 is lower than Close.
    # The dip might bring Close close to SMA50.

    strategy = MedallionIsaStrategy("TEST", df, check_mode=True)
    res = strategy.analyze()

    # Since we can't easily guarantee RSI < 15 with synthetic linear data without trial/error,
    # let's assert that it returns *something* valid or we check logic manually.
    # Actually, Rsi(3) of 3 down days (1%, 2%, 3% drop) is definitely < 15.

    assert res is not None
    assert "MEDALLION" in res['signal']
    assert res['vol_spike'] == True
    assert res['score'] >= 95

def test_medallion_isa_no_vol_spike():
    # Uptrend, Low RSI, Normal Vol
    df = create_mock_df(trend="UP", rsi_mode="LOW", vol_mode="LOW")

    strategy = MedallionIsaStrategy("TEST", df, check_mode=True)
    res = strategy.analyze()

    assert res is not None
    assert "MEDALLION" in res['signal']
    assert res['vol_spike'] == False
    assert res['score'] == 85 # 85 for normal vol

def test_medallion_isa_downtrend():
    # Downtrend
    df = create_mock_df(trend="DOWN", rsi_mode="LOW", vol_mode="HIGH")

    strategy = MedallionIsaStrategy("TEST", df, check_mode=True)
    res = strategy.analyze()

    # In check_mode, returns AVOID
    assert res is not None
    assert "AVOID" in res['signal']

def test_medallion_isa_no_trigger():
    # Uptrend, Normal RSI
    df = create_mock_df(trend="UP", rsi_mode="HIGH", vol_mode="HIGH") # rsi_mode != LOW

    strategy = MedallionIsaStrategy("TEST", df, check_mode=False) # Not check mode
    res = strategy.analyze()

    # Should return None because no trigger and not check_mode
    assert res is None
