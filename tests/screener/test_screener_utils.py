import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from option_auditor.common.screener_utils import ScreeningRunner, resolve_region_tickers, DEFAULT_RSI_LENGTH

def test_constants_availability():
    assert DEFAULT_RSI_LENGTH == 14

def test_resolve_region_tickers_defaults():
    tickers = resolve_region_tickers("us")
    assert len(tickers) > 0
    assert "AAPL" in tickers or "SPY" in tickers # Check for common tickers

@patch("option_auditor.common.screener_utils.fetch_batch_data_safe")
def test_screening_runner_run(mock_fetch):
    # Setup mock data
    mock_df = pd.DataFrame({
        "Close": [100, 101, 102],
        "Volume": [1000, 1000, 1000]
    }, index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]))

    # Mock return: Flat DF for single ticker
    mock_fetch.return_value = mock_df

    runner = ScreeningRunner(ticker_list=["AAPL"], time_frame="1d", region="us")

    def strategy(ticker, df):
        return {"ticker": ticker, "last_price": df['Close'].iloc[-1]}

    results = runner.run(strategy)

    assert len(results) == 1
    assert results[0]["ticker"] == "AAPL"
    assert results[0]["last_price"] == 102

@patch("option_auditor.common.screener_utils.fetch_batch_data_safe")
def test_screening_runner_empty(mock_fetch):
    mock_fetch.return_value = pd.DataFrame()

    runner = ScreeningRunner(ticker_list=["AAPL"], time_frame="1d", region="us")

    def strategy(ticker, df):
        return {"ticker": ticker}

    # Even if batch fetch fails, it might try individually inside?
    # No, runner._fetch_data returns empty, so ticker_data_map is empty.
    # But runner loops over self.ticker_list.
    # Inside loop, it calls prepare_data_for_ticker.
    # prepare_data_for_ticker calls fetch_data_with_retry if source is empty.
    # We need to mock fetch_data_with_retry too if we want it to succeed or fail gracefully.

    with patch("option_auditor.common.data_utils.fetch_data_with_retry") as mock_retry:
        mock_retry.return_value = pd.DataFrame() # Fail retry too
        results = runner.run(strategy)
        assert len(results) == 0
