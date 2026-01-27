
import pytest
from unittest.mock import patch, MagicMock
from option_auditor import screener

def test_screen_isa_region_selection():
    """
    Test that the ISA screener selects the correct ticker list based on the region parameter.
    We mock _get_filtered_sp500, get_uk_euro_tickers, get_indian_tickers and yfinance/pandas_ta to avoid network calls.
    """

    # Mocks
    mock_get_sp500 = MagicMock(return_value=["SPY", "AAPL"])
    mock_get_uk = MagicMock(return_value=["AZN.L", "BP.L"])
    mock_get_india = MagicMock(return_value=["RELIANCE.NS", "TCS.NS"])

    with patch('option_auditor.common.screener_utils._get_filtered_sp500', mock_get_sp500), \
         patch('option_auditor.common.screener_utils.get_uk_euro_tickers', mock_get_uk), \
         patch('option_auditor.common.screener_utils.get_indian_tickers', mock_get_india), \
         patch('option_auditor.screener.yf.download') as mock_download, \
              patch('option_auditor.common.screener_utils.SECTOR_COMPONENTS', {"WATCH": ["WATCH1", "SPY"]}):

         # Mock download response to avoid crash
         mock_download.return_value = MagicMock()

         # 1. Test US/Default
         screener.screen_trend_followers_isa(region="us")
         # Should call sp500 + WATCH
         # Since we can't easily check the list passed to download because it's merged,
         # we can inspect what was called or just rely on logic.
         # But wait, download is called with the list.
         args, _ = mock_download.call_args
         ticker_list_arg = args[0]
         assert "SPY" in ticker_list_arg
         assert "WATCH1" in ticker_list_arg
         assert "AZN.L" not in ticker_list_arg

         # 2. Test UK/Euro
         screener.screen_trend_followers_isa(region="uk_euro")
         args, _ = mock_download.call_args
         ticker_list_arg = args[0]
         assert "AZN.L" in ticker_list_arg
         assert "SPY" not in ticker_list_arg

         # 3. Test India
         screener.screen_trend_followers_isa(region="india")
         args, _ = mock_download.call_args
         ticker_list_arg = args[0]
         assert "RELIANCE.NS" in ticker_list_arg
         assert "SPY" not in ticker_list_arg

         # 4. Test SP500 explicit
         screener.screen_trend_followers_isa(region="sp500")
         args, _ = mock_download.call_args
         ticker_list_arg = args[0]
         assert "SPY" in ticker_list_arg
         assert "WATCH1" in ticker_list_arg # S&P500 mode also includes WATCH list in screener.py logic I added
