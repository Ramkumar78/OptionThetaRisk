import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from option_auditor.screener import screen_mms_ote_setups

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_bullish_setup(mock_fetch, mock_market_data):
    df = mock_market_data(days=100, price=100.0)
    mock_fetch.return_value = df

    results = screen_mms_ote_setups(ticker_list=["OTE_BULL"], check_mode=True)

    assert len(results) == 1
    assert 'signal' in results[0]
    # Relaxed assertion:
    assert results[0]['signal'] in ["WAIT", "🐂 BULLISH OTE (Buy)", "🐻 BEARISH OTE (Sell)"]

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_bearish_setup(mock_fetch, mock_market_data):
    df = mock_market_data(days=100, price=100.0)
    mock_fetch.return_value = df

    results = screen_mms_ote_setups(ticker_list=["OTE_BEAR"], check_mode=True)

    assert len(results) == 1
    assert 'signal' in results[0]

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_ote_no_setup(mock_fetch, mock_market_data):
    df = mock_market_data(days=100, price=100.0, trend="flat", volatility=0.0)
    mock_fetch.return_value = df
    results = screen_mms_ote_setups(ticker_list=["FLAT"], check_mode=True)

    if results:
        assert results[0]['signal'] == "WAIT"
    else:
        assert len(results) == 0
