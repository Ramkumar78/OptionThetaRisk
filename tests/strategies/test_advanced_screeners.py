import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.strategies.liquidity import screen_liquidity_grabs
from option_auditor.strategies.rsi_divergence import RsiDivergenceStrategy

# --- Helpers ---

def create_ohlcv(length=100, start_price=100.0, trend=0.0):
    dates = pd.date_range(start='2023-01-01', periods=length, freq='D')
    prices = [start_price + (i * trend) for i in range(length)]

    df = pd.DataFrame({
        'Open': prices,
        'High': [p + 2 for p in prices],
        'Low': [p - 2 for p in prices],
        'Close': prices,
        'Volume': [100000] * length
    }, index=dates)
    return df

# --- Liquidity Grab Tests ---

@pytest.fixture
def liquidity_strategy_extractor():
    """
    Captures the inner 'strategy' function from screen_liquidity_grabs
    by mocking the ScreeningRunner.run method.
    """
    with patch("option_auditor.strategies.liquidity.ScreeningRunner") as MockRunner:
        captured_strategy = {}

        # Define what run() does: capture the function
        def side_effect(func):
            captured_strategy['func'] = func
            return []

        instance = MockRunner.return_value
        instance.run.side_effect = side_effect

        # Trigger the extraction
        screen_liquidity_grabs(ticker_list=["TEST"])

        yield captured_strategy.get('func')

def test_liquidity_bullish_sweep(liquidity_strategy_extractor):
    strategy_func = liquidity_strategy_extractor
    assert strategy_func is not None, "Failed to capture strategy function"

    # 1. Setup Data with a Swing Low
    # We need a swing low at index 50.
    # T-1 (49): Low=102
    # T (50): Low=100 (SWING LOW)
    # T+1 (51): Low=102
    # Current (52): Low=99 (Sweep), Close=101 (Rejection)

    df = create_ohlcv(length=60, start_price=110)

    # Create Swing Low at index 50
    df.iloc[49, df.columns.get_loc('Low')] = 105.0
    df.iloc[50, df.columns.get_loc('Low')] = 100.0 # Swing Low
    df.iloc[50, df.columns.get_loc('High')] = 102.0
    df.iloc[51, df.columns.get_loc('Low')] = 105.0

    # Ensure surrounding highs don't interfere with swing logic (Swing High check needs valid neighbors)
    # The logic checks: Low < Prev and Low < Next.
    # 100 < 105 and 100 < 105. YES.

    # Current Candle (Last one) - needs to sweep 100
    last_idx = -1
    df.iloc[last_idx, df.columns.get_loc('Low')] = 99.0  # Sweep below 100
    df.iloc[last_idx, df.columns.get_loc('Close')] = 101.0 # Close above 100 (Rejection)
    df.iloc[last_idx, df.columns.get_loc('High')] = 105.0

    # Add Volume Spike
    avg_vol = df['Volume'].mean()
    df.iloc[last_idx, df.columns.get_loc('Volume')] = avg_vol * 2.0

    # Run Strategy
    result = strategy_func("TEST", df)

    assert result is not None
    assert "🐂 BULLISH SWEEP" in result['signal']
    assert result['breakout_level'] == 100.0
    assert "(Vol Spike)" in result['signal']

def test_liquidity_bearish_sweep(liquidity_strategy_extractor):
    strategy_func = liquidity_strategy_extractor

    df = create_ohlcv(length=60, start_price=90)

    # Create Swing High at index 50
    # T-1: High 105
    # T: High 110 (SWING HIGH)
    # T+1: High 105
    df.iloc[49, df.columns.get_loc('High')] = 105.0
    df.iloc[50, df.columns.get_loc('High')] = 110.0
    df.iloc[50, df.columns.get_loc('Low')] = 108.0
    df.iloc[51, df.columns.get_loc('High')] = 105.0

    # Current Candle (Last)
    last_idx = -1
    df.iloc[last_idx, df.columns.get_loc('High')] = 111.0 # Sweep above 110
    df.iloc[last_idx, df.columns.get_loc('Close')] = 109.0 # Close below 110 (Rejection)
    df.iloc[last_idx, df.columns.get_loc('Low')] = 100.0

    # Run Strategy
    result = strategy_func("TEST", df)

    assert result is not None
    assert "🐻 BEARISH SWEEP" in result['signal']
    assert result['breakout_level'] == 110.0

def test_liquidity_no_sweep(liquidity_strategy_extractor):
    strategy_func = liquidity_strategy_extractor

    df = create_ohlcv(length=60, start_price=100)
    # Just a trend, no sweeps of recent swings

    result = strategy_func("TEST", df)
    assert result is None


# --- RSI Divergence Tests ---

def test_rsi_bearish_divergence():
    # Setup Data
    # Bearish Div: Price Higher High, RSI Lower High
    length = 50
    df = create_ohlcv(length=length, start_price=100)

    # Create Peaks for Price
    # Peak 1 at index 30
    df.iloc[30, df.columns.get_loc('Close')] = 150.0 # High
    # Ensure neighbors are lower for argrelextrema (order=3)
    # 27,28,29 < 150 > 31,32,33
    for i in range(1, 4):
        df.iloc[30-i, df.columns.get_loc('Close')] = 140.0
        df.iloc[30+i, df.columns.get_loc('Close')] = 140.0

    # Peak 2 at index 45 (Recent)
    df.iloc[45, df.columns.get_loc('Close')] = 160.0 # Higher High
    for i in range(1, 4):
        df.iloc[45-i, df.columns.get_loc('Close')] = 140.0
        # For forward neighbors, we are near end of DF (length 50).
        # 45+1=46, 45+2=47, 45+3=48. All < 50. Safe.
        df.iloc[45+i, df.columns.get_loc('Close')] = 140.0

    # Current index is 49. (49-45 = 4 <= 5). So valid recent peak.

    # Mock RSI
    # We need RSI to have peaks at 30 and 45.
    # Peak 1 (30): RSI = 70
    # Peak 2 (45): RSI = 60 (Lower High)

    mock_rsi = pd.Series([50.0] * length, index=df.index)
    mock_rsi.iloc[30] = 70.0
    mock_rsi.iloc[45] = 60.0
    # Make sure neighbors are lower
    for i in range(1, 4):
        mock_rsi.iloc[30-i] = 60.0
        mock_rsi.iloc[30+i] = 60.0
        mock_rsi.iloc[45-i] = 50.0
        mock_rsi.iloc[45+i] = 50.0

    # Patch pandas_ta.rsi
    with patch('pandas_ta.rsi', return_value=mock_rsi):
        strategy = RsiDivergenceStrategy("TEST", df)
        result = strategy.analyze()

    assert result is not None
    assert result['signal'] == "🐻 BEARISH DIVERGENCE"
    assert result['verdict'] == "🐻 BEARISH DIVERGENCE"

def test_rsi_bullish_divergence():
    # Setup Data
    # Bullish Div: Price Lower Low, RSI Higher Low
    length = 50
    df = create_ohlcv(length=length, start_price=100)

    # Create Valleys for Price
    # Valley 1 at index 30
    df.iloc[30, df.columns.get_loc('Close')] = 50.0
    for i in range(1, 4):
        df.iloc[30-i, df.columns.get_loc('Close')] = 60.0
        df.iloc[30+i, df.columns.get_loc('Close')] = 60.0

    # Valley 2 at index 45 (Recent)
    df.iloc[45, df.columns.get_loc('Close')] = 40.0 # Lower Low
    for i in range(1, 4):
        df.iloc[45-i, df.columns.get_loc('Close')] = 60.0
        df.iloc[45+i, df.columns.get_loc('Close')] = 60.0

    # Mock RSI
    # Valley 1 (30): RSI = 30
    # Valley 2 (45): RSI = 40 (Higher Low)

    mock_rsi = pd.Series([50.0] * length, index=df.index)
    mock_rsi.iloc[30] = 30.0
    mock_rsi.iloc[45] = 40.0

    # Make sure neighbors are higher (Valley)
    for i in range(1, 4):
        mock_rsi.iloc[30-i] = 40.0
        mock_rsi.iloc[30+i] = 40.0
        mock_rsi.iloc[45-i] = 50.0
        mock_rsi.iloc[45+i] = 50.0

    # Patch pandas_ta.rsi
    with patch('pandas_ta.rsi', return_value=mock_rsi):
        strategy = RsiDivergenceStrategy("TEST", df)
        result = strategy.analyze()

    assert result is not None
    assert result['signal'] == "🐂 BULLISH DIVERGENCE"

def test_rsi_no_divergence():
    # Price Higher High, RSI Higher High (Convergence)
    length = 50
    df = create_ohlcv(length=length, start_price=100)

    # Peak 1 at 30
    df.iloc[30, df.columns.get_loc('Close')] = 150.0
    for i in range(1, 4):
        df.iloc[30-i, df.columns.get_loc('Close')] = 140.0
        df.iloc[30+i, df.columns.get_loc('Close')] = 140.0

    # Peak 2 at 45
    df.iloc[45, df.columns.get_loc('Close')] = 160.0 # Higher
    for i in range(1, 4):
        df.iloc[45-i, df.columns.get_loc('Close')] = 140.0
        df.iloc[45+i, df.columns.get_loc('Close')] = 140.0

    mock_rsi = pd.Series([50.0] * length, index=df.index)
    mock_rsi.iloc[30] = 70.0
    mock_rsi.iloc[45] = 80.0 # Higher (Convergence)

    for i in range(1, 4):
        mock_rsi.iloc[30-i] = 60.0
        mock_rsi.iloc[30+i] = 60.0
        mock_rsi.iloc[45-i] = 70.0
        mock_rsi.iloc[45+i] = 70.0

    with patch('pandas_ta.rsi', return_value=mock_rsi):
        strategy = RsiDivergenceStrategy("TEST", df)
        result = strategy.analyze()

    assert result is None
