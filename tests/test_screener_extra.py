import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from option_auditor import screener
import time

# Mock Data - Redefined with longer history for SMA50 and Turtle
def mock_yf_download(*args, **kwargs):
    # Determine the tickers being requested
    tickers = args[0] if args else kwargs.get('tickers')
    if isinstance(tickers, str):
        tickers = tickers.split()

    # Need > 50 periods for SMA50
    periods = 60
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')

    data = {}
    for ticker in tickers:
        # Create a price series that triggers signals
        # Linear growth: 100, 101, ... 159.
        # This is a strong uptrend. RSI will be high. Price > SMA50.
        closes = [100.0 + i for i in range(periods)]

        # Trigger Turtle Breakout at the end
        # Last close jumps significantly to exceed previous 20-day high
        closes[-1] = closes[-2] + 20 # Big jump

        highs = [c + 5 for c in closes]
        lows = [c - 5 for c in closes]
        opens = [c for c in closes]

        data[(ticker, 'Close')] = closes
        data[(ticker, 'High')] = highs
        data[(ticker, 'Low')] = lows
        data[(ticker, 'Open')] = opens
        data[(ticker, 'Volume')] = [1000000 for _ in range(periods)]

    # Create MultiIndex DataFrame
    df = pd.DataFrame(data, index=dates)
    df.columns = pd.MultiIndex.from_tuples(df.columns)

    return df

class TestScreenerExtra:
    @patch('option_auditor.screener.yf.download')
    def test_screen_market(self, mock_download):
        mock_download.side_effect = mock_yf_download

        # Mocking SECTOR_NAMES and SECTOR_COMPONENTS
        with patch('option_auditor.screener.SECTOR_NAMES', {"TEST": "Test Sector"}), \
            patch('option_auditor.screener.SECTOR_COMPONENTS', {"TEST": ["AAPL"]}):

            results = screener.screen_market(iv_rank_threshold=20, rsi_threshold=80)

            # Key in results is "Sector Name (Code)" -> "Test Sector (TEST)"
            expected_key = "Test Sector (TEST)"
            assert expected_key in results
            assert len(results[expected_key]) > 0
            # Check structure
            item = results[expected_key][0]
            assert "ticker" in item
            assert "price" in item
            assert "rsi" in item

    @patch('option_auditor.screener.yf.download')
    def test_screen_turtle(self, mock_download):
        mock_download.side_effect = mock_yf_download

        tickers = ["AAPL", "GOOGL"]
        # Turtle needs len(df) >= 21. Mock currently returns 60.
        results = screener.screen_turtle_setups(ticker_list=tickers, time_frame="1d")

        # Since mock data is strictly increasing, it will be a breakout.
        assert len(results) > 0
        assert results[0]["ticker"] in tickers

    @patch('option_auditor.screener.yf.download')
    def test_screen_darvas(self, mock_download):
        mock_download.side_effect = mock_yf_download

        tickers = ["AAPL"]
        results = screener.screen_darvas_box(ticker_list=tickers)

        # Even if empty, it should return a list
        assert isinstance(results, list)

    @patch('option_auditor.screener.yf.download')
    def test_screen_ema(self, mock_download):
        mock_download.side_effect = mock_yf_download

        tickers = ["AAPL"]
        results = screener.screen_5_13_setups(ticker_list=tickers)

        assert isinstance(results, list)

    def test_uk_euro_tickers(self):
        tickers = screener.get_uk_euro_tickers()
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        # Check if suffixes are correct
        assert any(t.endswith(".L") or t.endswith(".PA") or t.endswith(".AS") for t in tickers)

    def test_indian_tickers(self):
        tickers = screener.get_indian_tickers()
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        assert any(t.endswith(".NS") for t in tickers)

    @patch('option_auditor.screener.yf.download')
    @patch('time.sleep', return_value=None)
    def test_intraday_data_fetch(self, mock_sleep, mock_download):
        # Test internal helper _prepare_data_for_ticker for intraday
        mock_df = pd.DataFrame({
            "Close": [100]*10,
            "High": [105]*10,
            "Low": [95]*10,
            "Open": [100]*10,
            "Volume": [1000]*10
        }, index=pd.date_range("2023-01-01", periods=10, freq="h"))

        mock_download.return_value = mock_df

        # Correct signature: ticker, data_source, time_frame, period, yf_interval, resample_rule, is_intraday
        df = screener._prepare_data_for_ticker("AAPL", None, "1h", "1d", "1h", None, True)
        assert not df.empty
        # Note: _prepare_data_for_ticker DOES NOT add indicators like RSI. That happens in the caller functions.
        assert "Close" in df.columns

    def test_screen_sectors_coverage(self):
        # Coverage for screen_sectors
        with patch('option_auditor.screener.SECTOR_NAMES', {"TEST": "Test Sector"}), \
            patch('option_auditor.screener._screen_tickers') as mock_screen:
            mock_screen.return_value = [{"ticker": "TEST", "price": 100}]

            results = screener.screen_sectors()
            assert len(results) == 1
            assert results[0]["ticker"] == "TEST"
