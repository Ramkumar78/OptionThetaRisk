import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_alpha_101

# Mock Data Generation Helper
def create_mock_df(prices, length=20):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='D')

    data = {
        'Open': [prices['Open']] * length,
        'High': [prices['High']] * length,
        'Low': [prices['Low']] * length,
        'Close': [prices['Close']] * length,
        'Volume': [1000000] * length
    }
    df = pd.DataFrame(data, index=dates)
    return df

# Patching fetch_batch_data_safe in screener_utils where ScreeningRunner is defined
@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('option_auditor.common.screener_utils._resolve_region_tickers')
def test_screen_alpha_101_strong_buy(mock_resolve, mock_fetch):
    mock_resolve.return_value = ['AAPL']

    # Strong Buy: Close at High
    prices = {'Open': 100.0, 'High': 110.0, 'Low': 100.0, 'Close': 110.0}
    df = create_mock_df(prices, length=20)

    mock_fetch.return_value = df

    results = screen_alpha_101(ticker_list=['AAPL'])

    assert len(results) == 1
    res = results[0]
    assert res['ticker'] == 'AAPL'
    assert "STRONG BUY" in res['signal']
    assert res['alpha_101'] > 0.9

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('option_auditor.common.screener_utils._resolve_region_tickers')
def test_screen_alpha_101_strong_sell(mock_resolve, mock_fetch):
    mock_resolve.return_value = ['TSLA']

    # Strong Sell: Close at Low
    prices = {'Open': 110.0, 'High': 110.0, 'Low': 100.0, 'Close': 100.0}
    df = create_mock_df(prices, length=20)
    mock_fetch.return_value = df

    results = screen_alpha_101(ticker_list=['TSLA'])

    assert len(results) == 1
    res = results[0]
    assert "STRONG SELL" in res['signal']
    assert res['alpha_101'] < -0.9

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('option_auditor.common.screener_utils._resolve_region_tickers')
def test_screen_alpha_101_neutral_filter(mock_resolve, mock_fetch):
    mock_resolve.return_value = ['MSFT']

    # Neutral: Close = Open (Doji)
    prices = {'Open': 105.0, 'High': 110.0, 'Low': 100.0, 'Close': 105.0}
    df = create_mock_df(prices, length=20)
    mock_fetch.return_value = df

    results = screen_alpha_101(ticker_list=['MSFT'])

    assert len(results) == 0
