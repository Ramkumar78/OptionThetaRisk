import pandas as pd
import pytest
from option_auditor.strategies.grandmaster import GrandmasterStrategy
from option_auditor.common.signal_type import SignalType

def test_grandmaster_initialization():
    strategy = GrandmasterStrategy()
    assert strategy.name == "Grandmaster"
    assert strategy.screener is not None

def test_grandmaster_logic_trend_template():
    strategy = GrandmasterStrategy()

    # Create synthetic data that matches Minervini Trend Template
    # We need enough data for 200 SMA and 252 High/Low
    # Let's create 300 days of data
    dates = pd.date_range(start="2020-01-01", periods=300, freq="D")

    # We construct a price series that is clearly in an uptrend
    # Linear growth: 100 to 400
    prices = [100 + i for i in range(300)]

    df = pd.DataFrame({
        "close": prices,
        "Close": prices, # Ensure both exist for robustness
        "high": [p + 5 for p in prices],
        "low": [p - 5 for p in prices],
        "open": prices,
        "volume": [1000000] * 300
    }, index=dates)

    result = strategy.generate_signals(df)

    # Check last row
    last_row = result.iloc[-1]

    # Calculate expected values manually
    # SMA 50 at 299: mean(250..299) approx 274.5
    # SMA 150 at 299: mean(150..299) approx 224.5
    # SMA 200 at 299: mean(100..299) approx 199.5
    # Close 299: 399
    # High 52 (252 days): 399
    # Low 52 (252 days): 399 - 251 = 148

    # Conditions:
    # 1. Close > 150 (399 > 224.5) OK
    # 2. Close > 200 (399 > 199.5) OK
    # 3. 150 > 200 (224.5 > 199.5) OK
    # 4. 50 > 150 (274.5 > 224.5) OK
    # 5. Close > 50 (399 > 274.5) OK
    # 6. Close > Low52 * 1.3 (399 > 148 * 1.3 = 192.4) OK
    # 7. Close > High52 * 0.75 (399 > 399 * 0.75 = 299.25) OK

    # Expect BUY signal
    assert last_row['signal'] == SignalType.BUY.value

def test_grandmaster_logic_downtrend():
    strategy = GrandmasterStrategy()
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

    result = strategy.generate_signals(df)
    last_row = result.iloc[-1]

    # Close < SMA 50 implies SELL
    assert last_row['signal'] == SignalType.SELL.value
