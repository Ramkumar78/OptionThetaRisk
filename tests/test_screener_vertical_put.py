import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.strategies.vertical_spreads import screen_vertical_put_spreads
from datetime import date, timedelta

# Sample Data Creation
def create_trend_df():
    dates = pd.date_range(end=date.today(), periods=250)
    # create a bullish trend
    prices = np.linspace(100, 200, 250)
    df = pd.DataFrame({'Close': prices, 'Volume': [2000000]*250}, index=dates)
    return df

@patch('option_auditor.strategies.vertical_spreads.fetch_batch_data_safe')
@patch('option_auditor.strategies.vertical_spreads.yf.Ticker')
@patch('option_auditor.strategies.vertical_spreads.resolve_region_tickers')
def test_screen_vertical_put_spreads_refactor(mock_resolve, mock_ticker_cls, mock_fetch):
    # Setup Ticker List
    mock_resolve.return_value = ['TEST']

    # Setup Batch Data
    df = create_trend_df()
    # fetch_batch_data_safe returns a DataFrame (single level if 1 ticker or flattened?)
    # The code handles both. Let's provide a MultiIndex to simulate real batch return
    cols = pd.MultiIndex.from_product([['TEST'], ['Close', 'Volume']])
    # We need to broadcast the df columns to this multiindex
    # But simpler to just return a dict-like or standard multiindex df
    # Let's return a simple MultiIndex DF

    # Actually, let's look at how the function handles it.
    # iterator = [(t, data[t]) for t in data.columns.levels[0] if t in ticker_list]
    # So it expects MultiIndex with Ticker at level 0.

    df_multi = pd.DataFrame(index=df.index)
    df_multi[('TEST', 'Close')] = df['Close']
    df_multi[('TEST', 'Volume')] = df['Volume']
    df_multi.columns = pd.MultiIndex.from_tuples(df_multi.columns)

    mock_fetch.return_value = df_multi

    # Setup yf.Ticker Mock
    mock_instance = MagicMock()
    mock_ticker_cls.return_value = mock_instance

    # Mock Calendar (Earnings safe)
    mock_instance.calendar = {'Earnings Date': [date.today() + timedelta(days=60)]}

    # Mock Options Chain
    # We need expirations
    target_date = date.today() + timedelta(days=35) # 35 DTE
    target_date_str = target_date.strftime("%Y-%m-%d")
    mock_instance.options = [target_date_str]

    # Mock Option Chain Object
    mock_chain = MagicMock()
    # Puts DataFrame
    # Need columns: volume, openInterest, strike, impliedVolatility, bid, ask, lastPrice

    curr_price = 200.0 # From our trend df

    puts_data = {
        'strike': [180, 185, 190, 195, 200],
        'volume': [2000, 2000, 2000, 2000, 2000],
        'openInterest': [1000, 1000, 1000, 1000, 1000],
        'impliedVolatility': [0.25, 0.25, 0.25, 0.25, 0.25], # Higher than HV (HV will be low for linear trend)
        'bid': [1.0, 1.5, 2.0, 3.0, 5.0],
        'ask': [1.2, 1.7, 2.2, 3.2, 5.2],
        'lastPrice': [1.1, 1.6, 2.1, 3.1, 5.1]
    }
    mock_chain.puts = pd.DataFrame(puts_data)
    mock_instance.option_chain.return_value = mock_chain

    # Run Function
    results = screen_vertical_put_spreads(['TEST'])

    # Verify
    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == 'TEST'
    assert res['verdict'] == '🟢 HIGH PROB'
    assert 'Bull Put' in res['setup_name']

    # Verify logic was exercised
    mock_fetch.assert_called()
    mock_ticker_cls.assert_called_with('TEST')
