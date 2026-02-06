import pytest
import pandas as pd
import numpy as np
from option_auditor.strategies.rsi_reversal import RsiReversalStrategy

@pytest.fixture
def strategy():
    return RsiReversalStrategy()

def test_add_indicators(strategy):
    # Create simple DF
    dates = pd.date_range('2023-01-01', periods=20)
    df = pd.DataFrame({
        'Close': np.random.rand(20) * 100
    }, index=dates)

    df_result = strategy.add_indicators(df)
    assert 'rsi' in df_result.columns

def test_should_buy_signal(strategy):
    # Code Logic: Buy if Close < LowerBB AND RSI < 30

    # Create a DataFrame with necessary columns
    df = pd.DataFrame({
        'Close':      [100, 90, 100, 90, 100],
        'BBL_20_2.0': [95,  95, 95,  95, 95], # Lower BB
        'rsi':        [40,  25, 25,  35, 40]
    })

    # Index 0: Close(100) > BB(95), RSI(40) > 30. -> False
    assert strategy.should_buy(0, df, {}) == False

    # Index 1: Close(90) < BB(95) AND RSI(25) < 30. -> True (Dip Buy)
    assert strategy.should_buy(1, df, {}) == True

    # Index 2: Close(100) > BB(95) but RSI(25) < 30. -> False (Price too high)
    assert strategy.should_buy(2, df, {}) == False

    # Index 3: Close(90) < BB(95) but RSI(35) > 30. -> False (RSI too high)
    assert strategy.should_buy(3, df, {}) == False

def test_should_sell_signal(strategy):
    # RSI: ... 71, 69 ...
    df = pd.DataFrame({
        'rsi': [50, 75, 71, 69, 50]
    })

    # Index 2: 71 (prev=75). No cross below 70.
    assert strategy.should_sell(2, df, {}) == (False, "")

    # Index 3: 69 (prev=71). Cross below 70.
    should_sell, reason = strategy.should_sell(3, df, {})
    assert should_sell == True
    assert "RSI Cross Below 70" in reason

    # Index 4: 50 (prev=69). Already below.
    assert strategy.should_sell(4, df, {}) == (False, "")

def test_get_initial_stop_target(strategy):
    row = pd.Series({'Close': 100.0})
    atr = 5.0 # Unused
    stop, target = strategy.get_initial_stop_target(row, atr)

    assert stop == 98.0 # 2% below 100
    assert target == 0.0

def test_analyze(strategy):
    # Create a DF that has enough data
    dates = pd.date_range('2023-01-01', periods=30)
    prices = [100.0] * 30

    df = pd.DataFrame({
        'Close': prices,
        'High': prices,
        'Low': prices,
        'Volume': [1000] * 30
    }, index=dates)

    result = strategy.analyze(df)

    assert result is not None
    assert "signal" in result
    assert "rsi" in result
