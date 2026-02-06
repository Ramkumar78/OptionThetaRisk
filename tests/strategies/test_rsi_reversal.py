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
    # RSI: ... 29, 31 ...
    df = pd.DataFrame({
        'rsi': [50, 25, 29, 31, 50]
    })

    # Index 2: 29 (prev=25). No cross above 30.
    assert strategy.should_buy(2, df, {}) == False

    # Index 3: 31 (prev=29). Cross above 30.
    assert strategy.should_buy(3, df, {}) == True

    # Index 4: 50 (prev=31). Already above.
    assert strategy.should_buy(4, df, {}) == False

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
        'Low': prices
    }, index=dates)

    result = strategy.analyze(df)

    assert result is not None
    assert "signal" in result
    assert "rsi" in result
