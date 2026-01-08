import pytest
from unittest.mock import patch
import pandas as pd
from option_auditor.screener import screen_5_13_setups

@patch('option_auditor.screener.fetch_batch_data_safe')
def test_screen_ema_fresh_breakout(mock_fetch, mock_market_data):
    # Fresh 5/13 Breakout:
    # Curr 5 > 13
    # Prev 5 <= 13

    df = mock_market_data(days=50, price=100.0)

    # Mock EMAs via patching pandas_ta?
    # Or just manipulate price such that EMA calc works?
    # Easier to patch pandas_ta inside the function or trust the calculation logic if we supply enough data.
    # But calculating exact EMA with 50 points is hard to control precisely.
    # We will Mock pandas_ta to return specific Series.

    import pandas_ta as ta

    # We create a dataframe with enough length

    mock_fetch.return_value = df

    # We need to mock pandas_ta.ema call.
    # The function calls ta.ema(df['Close'], length=5) etc.

    # We can patch pandas_ta imported in screener.py
    # But screener imports it inside function or top level?
    # screener.py: "import pandas_ta as ta" inside try/except block usually, or top level.
    # In `screen_5_13_setups`, it imports inside.

    with patch('option_auditor.screener.screen_5_13_setups') as mock_screener:
         # Wait, I am mocking the function I am testing. Bad idea.
         pass

    # Let's rely on `_prepare_data_for_ticker` returning a DF, and then mock the columns manually?
    # The function calls `ta.ema(...)` and assigns to `df['EMA_5']`.
    # If we patch `pandas_ta.ema`, we can control the output series.

    with patch('pandas_ta.ema') as mock_ema:
        # We need to return different series based on length arg
        def side_effect(close, length):
            vals = pd.Series([100.0] * len(close), index=close.index)
            if length == 5:
                # 5 > 13 at end
                vals.iloc[-1] = 105.0
                vals.iloc[-2] = 100.0
            elif length == 13:
                vals.iloc[-1] = 102.0 # 105 > 102 (Cross)
                vals.iloc[-2] = 101.0 # 100 <= 101 (Prev was below)
            elif length == 21:
                vals[:] = 90.0
            return vals

        mock_ema.side_effect = side_effect

        # We also need to mock ATR since it is called
        with patch('pandas_ta.atr', return_value=pd.Series([1.0]*len(df), index=df.index)):
             results = screen_5_13_setups(ticker_list=["EMA"], check_mode=True)

             assert len(results) == 1
             assert "FRESH 5/13 BREAKOUT" in results[0]['signal']
             assert results[0]['color'] == "green"

@patch('option_auditor.screener.fetch_batch_data_safe')
def test_screen_ema_dump(mock_fetch, mock_market_data):
    df = mock_market_data(days=50, price=100.0)
    mock_fetch.return_value = df

    with patch('pandas_ta.ema') as mock_ema:
        def side_effect(close, length):
            vals = pd.Series([100.0] * len(close), index=close.index)
            if length == 5:
                # Cross below 13
                vals.iloc[-1] = 90.0
                vals.iloc[-2] = 105.0
            elif length == 13:
                vals.iloc[-1] = 100.0
                vals.iloc[-2] = 100.0
            elif length == 21:
                vals[:] = 80.0
            return vals

        mock_ema.side_effect = side_effect

        with patch('pandas_ta.atr', return_value=pd.Series([1.0]*len(df), index=df.index)):
             results = screen_5_13_setups(ticker_list=["DUMP"], check_mode=True)

             assert len(results) == 1
             assert "5/13 DUMP" in results[0]['signal']
             assert results[0]['color'] == "red"
