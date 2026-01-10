import pandas as pd
import pytest
from option_auditor.strategies.grandmaster_screener import GrandmasterScreener
from option_auditor.common.signal_type import SignalType

def test_grandmaster_initialization():
    strategy = GrandmasterScreener()
    assert strategy.name == "GrandmasterScreener"
    # assert strategy.screener is not None # BaseStrategy doesn't necessarily have a screener attribute

def test_grandmaster_logic_trend_template_with_breakout():
    strategy = GrandmasterScreener()

    # Create synthetic data that matches Minervini Trend Template
    # We need enough data for 200 SMA and 252 High/Low
    # Let's create 300 days of data
    dates = pd.date_range(start="2020-01-01", periods=300, freq="D")

    # We construct a price series that is clearly in an uptrend
    # Linear growth: 100 to 400
    prices = [100 + i for i in range(300)]

    # Volume needs to be high for breakout
    volumes = [1000000] * 300
    # Make the last day have high volume (RVol > 1.2)
    volumes[-1] = 1300000 # 1.3x average

    df = pd.DataFrame({
        "close": prices,
        "Close": prices,
        "high": [p + 5 for p in prices],
        "low": [p - 5 for p in prices],
        "open": prices,
        "volume": volumes,
        "Volume": volumes
    }, index=dates)

    # Force a breakout:
    # Current close needs to be > previous 20 day high.
    # In our linear series, every day is a new high, so technically every day breaks the 20-day high (of the previous day, which was lower).
    # prices[299] = 399.
    # Previous 20 days: 279..298. Max High was approx 298+5=303? No, linear growth.
    # prices[298] = 398. high[298] = 403.
    # prices[299] = 399.

    # Wait, if p[299]=399, and high[298]=403, then close is NOT > Donchian_High_20.
    # We need to make the current close HIGHER than the recent highs.
    # Let's flatten the price for 20 days then pop it.

    # Construct a flat base then breakout
    # Days 0-250: Linear uptrend to establish trend
    prices_trend = [100 + i for i in range(250)] # Ends at 349

    # Days 250-298: Consolidation (Flat around 350)
    prices_base = [350] * 49

    # Day 299: Breakout to 360
    prices_breakout = [360]

    all_prices = prices_trend + prices_base + prices_breakout

    # Update DataFrame
    df = pd.DataFrame({
        "close": all_prices,
        "high": [p + 2 for p in all_prices], # Tight range
        "low": [p - 2 for p in all_prices],
        "open": all_prices,
        "volume": [1000000] * 299 + [2000000] # huge volume spike on last day
    }, index=dates)

    # Ensure columns are duplicated as strategy might check Capitalized ones
    df['Close'] = df['close']
    df['High'] = df['high']
    df['Low'] = df['low']
    df['Volume'] = df['volume']

    result = strategy.generate_signals(df)
    last_row = result.iloc[-1]

    # Check RVol
    # Avg volume last 20 days (approx): (19*1M + 2M)/20 = 1.05M
    # Current Vol: 2M. RVol ~ 1.9 > 1.2. OK.

    # Check Trend
    # SMA 200 around 250ish. Close 360. OK.
    # SMA 50 around 350ish. Close 360. OK.

    # Check Breakout
    # Prev 20 day high was 352 (350+2).
    # Current close 360 > 352. OK.

    # Expect BUY signal
    assert last_row['signal'] == SignalType.BUY.value

    # Also check analyze() output
    analysis = strategy.analyze(df)
    assert analysis['signal'] == "BUY BREAKOUT"
    assert analysis['rvol'] > 1.2

def test_grandmaster_logic_watchlist_no_breakout():
    strategy = GrandmasterScreener()
    dates = pd.date_range(start="2020-01-01", periods=300, freq="D")

    # Strong uptrend but currently consolidating (no breakout)
    prices_trend = [100 + i for i in range(250)] # Ends at 349
    prices_base = [350] * 50 # Flat finish

    all_prices = prices_trend + prices_base

    df = pd.DataFrame({
        "close": all_prices,
        "high": [p + 2 for p in all_prices],
        "low": [p - 2 for p in all_prices],
        "open": all_prices,
        "volume": [1000000] * 300
    }, index=dates)

    # Columns copy
    df['Close'] = df['close']
    df['High'] = df['high']
    df['Low'] = df['low']
    df['Volume'] = df['volume']

    result = strategy.generate_signals(df)
    last_row = result.iloc[-1]

    # Should be HOLD (0) because trend is good but no breakout trigger
    assert last_row['signal'] == SignalType.HOLD.value

    # Analyze should return WATCHLIST
    analysis = strategy.analyze(df)
    assert analysis['signal'] == "WATCHLIST"

def test_grandmaster_logic_sell_downtrend():
    strategy = GrandmasterScreener()
    dates = pd.date_range(start="2020-01-01", periods=300, freq="D")

    # Downtrend: 400 to 100
    prices = [400 - i for i in range(300)]

    df = pd.DataFrame({
        "close": prices,
        "high": [p + 5 for p in prices],
        "low": [p - 5 for p in prices],
        "open": prices,
        "volume": [1000000] * 300
    }, index=dates)

    df['Close'] = df['close']
    df['High'] = df['high']
    df['Low'] = df['low']
    df['Volume'] = df['volume']

    result = strategy.generate_signals(df)
    last_row = result.iloc[-1]

    # Close < Donchian Low 20
    # In a continuous downtrend, current close is always the lowest
    # Prev 20 day low would be price[298] - 5 = 102 - 5 = 97?
    # Wait, prices are decreasing.
    # price[299] = 101.
    # prices[279..298] are all higher than 101.
    # Donchian Low 20 is min(low[279..298]).
    # min low is low[298] = 102 - 5 = 97.
    # price[299] = 101. 101 > 97. NOT A BREAKDOWN?

    # Let's force a breakdown.
    # Flat then drop.
    prices_flat = [300] * 280
    prices_drop = [250] * 20 # Drop to 250
    # On day 300, drop to 200

    # Actually, simplistic check:
    # If Close < Donchian_Low_20 (min of prev 20 days).
    # If we crash hard below previous range.

    prices = [300] * 299 + [200]
    df = pd.DataFrame({
        "close": prices,
        "high": [p + 5 for p in prices],
        "low": [p - 5 for p in prices],
        "open": prices,
        "volume": [1000000] * 300
    }, index=dates)
    df['Close'] = df['close']
    df['High'] = df['high']
    df['Low'] = df['low']
    df['Volume'] = df['volume']

    result = strategy.generate_signals(df)
    last_row = result.iloc[-1]

    # Prev 20 low was 295. Current close 200.
    # 200 < 295. SELL.
    assert last_row['signal'] == SignalType.SELL.value

    analysis = strategy.analyze(df)
    assert analysis['signal'] == "SELL/AVOID"
