import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from option_auditor.screener import screen_darvas_box, screen_5_13_setups, screen_market

@patch('option_auditor.screener.yf.download')
def test_darvas_box_screener(mock_download):
    mock_download.return_value = pd.DataFrame()
    results = screen_darvas_box(time_frame='1d')
    assert isinstance(results, list)
    assert len(results) == 0

@patch('option_auditor.screener.yf.download')
def test_ema_screener_empty(mock_download):
    mock_download.return_value = pd.DataFrame()
    results = screen_5_13_setups(time_frame='1d')
    assert isinstance(results, list)
    assert len(results) == 0

@patch('option_auditor.screener.yf.download')
def test_market_screener_params(mock_download):
    mock_download.return_value = pd.DataFrame()
    results = screen_market(iv_rank_threshold=20.0, rsi_threshold=70.0)
    assert isinstance(results, dict)
