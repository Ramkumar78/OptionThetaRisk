import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    resolve_region_tickers,
    DEFAULT_RSI_LENGTH,
    resolve_ticker,
    _norm_cdf,
    _calculate_put_delta,
    _get_filtered_sp500,
    run_screening_strategy
)
from option_auditor.common.constants import TICKER_NAMES

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

# --- Merged from test_screener_utils.py (formerly _extra) ---

# Mock Strategy Class for testing run_screening_strategy
class MockStrategy:
    def __init__(self, ticker, df, **kwargs):
        self.ticker = ticker
        self.df = df
        self.kwargs = kwargs

    def analyze(self):
        return {"ticker": self.ticker, "result": "ok", "kwargs": self.kwargs}

class MockStrategyNoKwargs:
    def __init__(self, ticker, df):
        self.ticker = ticker
        self.df = df

    def analyze(self):
        return {"ticker": self.ticker, "result": "ok_no_kwargs"}

# --- Tests for resolve_ticker ---
def test_resolve_ticker_exact():
    # If key exists, return it
    assert resolve_ticker("AAPL") == "AAPL"

def test_resolve_ticker_company_name():
    # If exact name match (case insensitive)
    # Using a known constant from memory or mocked
    # Let's mock constants for safety in unit test
    with patch.dict(TICKER_NAMES, {"TST": "Test Company Inc"}, clear=True):
        assert resolve_ticker("Test Company Inc") == "TST"
        assert resolve_ticker("TEST COMPANY INC") == "TST"

def test_resolve_ticker_partial_match():
    with patch.dict(TICKER_NAMES, {"TST": "Test Company Inc"}, clear=True):
        assert resolve_ticker("Test Company") == "TST"

def test_resolve_ticker_suffix():
    with patch.dict(TICKER_NAMES, {"VOD.L": "Vodafone"}, clear=True):
        # If input doesn't have dot, try adding .L
        assert resolve_ticker("VOD") == "VOD.L"

def test_resolve_ticker_fallback():
    assert resolve_ticker("UNKNOWN123") == "UNKNOWN123"

def test_resolve_ticker_empty():
    assert resolve_ticker(None) == ""
    assert resolve_ticker("") == ""

# --- Tests for Math Utils ---
def test_norm_cdf():
    # Known values for Standard Normal CDF
    assert _norm_cdf(0) == pytest.approx(0.5, abs=1e-5)
    assert 0.84 < _norm_cdf(1.0) < 0.842
    assert 0.977 < _norm_cdf(2.0) < 0.978
    assert _norm_cdf(-10) == 0.0
    assert _norm_cdf(10) == 1.0

def test_calculate_put_delta():
    # Deep ITM Put (Price << Strike) -> Delta near -1
    delta_itm = _calculate_put_delta(S=50, K=100, T=1, r=0.05, sigma=0.2)
    assert -1.1 <= delta_itm <= -0.9

    # Deep OTM Put (Price >> Strike) -> Delta near 0
    delta_otm = _calculate_put_delta(S=150, K=100, T=1, r=0.05, sigma=0.2)
    assert -0.1 <= delta_otm <= 0.1

    # ATM Put -> Delta around -0.36 for these params (due to drift)
    delta_atm = _calculate_put_delta(S=100, K=100, T=1, r=0.05, sigma=0.2)
    # Calculated as approx -0.36
    assert -0.4 <= delta_atm <= -0.3

    # Invalid input
    assert _calculate_put_delta(100, 100, -1, 0.05, 0.2) == -0.5

# --- Tests for _get_filtered_sp500 ---
@patch("option_auditor.common.screener_utils.get_sp500_tickers")
@patch("option_auditor.common.screener_utils.get_cached_market_data")
def test_get_filtered_sp500_cache_hit(mock_cache, mock_tickers):
    mock_tickers.return_value = ["A", "B"]

    # Mock Cache DF with MultiIndex
    # Ticker A: High Volume, High Price (Pass)
    # Ticker B: Low Volume (Fail)

    # Create simple DF
    dates = pd.date_range("2023-01-01", periods=250)

    df_a = pd.DataFrame({
        "Close": [100]*249 + [150], # Price > SMA200 (100.2)
        "Volume": [1000000]*250
    }, index=dates)

    df_b = pd.DataFrame({
        "Close": [100]*250,
        "Volume": [100]*250 # Low Volume
    }, index=dates)

    # MultiIndex construction
    df_a.columns = pd.MultiIndex.from_product([["A"], df_a.columns])
    df_b.columns = pd.MultiIndex.from_product([["B"], df_b.columns])

    full_df = pd.concat([df_a, df_b], axis=1)
    mock_cache.return_value = full_df

    result = _get_filtered_sp500(check_trend=True)
    assert "A" in result
    assert "B" not in result

@patch("option_auditor.common.screener_utils.get_sp500_tickers")
@patch("option_auditor.common.screener_utils.get_cached_market_data")
def test_get_filtered_sp500_fallback(mock_cache, mock_tickers):
    mock_tickers.return_value = ["A"]
    mock_cache.return_value = pd.DataFrame() # Empty cache

    # Should return raw list
    assert _get_filtered_sp500() == ["A"]

# --- Tests for ScreeningRunner ---
def test_screening_runner_configure_timeframe():
    # Test 1d
    runner = ScreeningRunner(time_frame="1d")
    assert runner.yf_interval == "1d"
    assert not runner.is_intraday

    # Test 1h
    runner = ScreeningRunner(time_frame="1h")
    assert runner.yf_interval == "1h"
    assert runner.is_intraday

    # Test custom minute
    runner = ScreeningRunner(time_frame="49m")
    assert runner.yf_interval == "5m"
    assert runner.resample_rule == "49min"

@patch("option_auditor.common.screener_utils.fetch_batch_data_safe")
@patch("option_auditor.common.screener_utils.get_cached_market_data")
def test_screening_runner_fetch_data_logic(mock_cache, mock_fetch):
    runner = ScreeningRunner(region="us", time_frame="1d")

    # Case 1: Live fetch (cache empty or ignored)
    mock_cache.return_value = pd.DataFrame() # Lookup only returns empty
    mock_fetch.return_value = pd.DataFrame({"A": [1,2,3]})

    data = runner._fetch_data(["A"])
    assert not data.empty
    mock_fetch.assert_called()

# --- Tests for run_screening_strategy ---
@patch("option_auditor.common.screener_utils.ScreeningRunner.run")
def test_run_screening_strategy_wrappers(mock_run):
    # Mock the internal run call to execute the passed wrapper function
    def side_effect(wrapper_func):
        # Simulate processing one ticker
        return [wrapper_func("AAPL", pd.DataFrame())]

    mock_run.side_effect = side_effect

    # Test with standard strategy
    results = run_screening_strategy(MockStrategy, ticker_list=["AAPL"], some_param=123)
    assert len(results) == 1
    assert results[0]['ticker'] == "AAPL"
    assert results[0]['kwargs']['some_param'] == 123

    # Test with strategy that doesn't accept kwargs (fallback)
    results_no_kw = run_screening_strategy(MockStrategyNoKwargs, ticker_list=["AAPL"], some_param=123)
    assert len(results_no_kw) == 1
    assert results_no_kw[0]['result'] == "ok_no_kwargs"

    # Test Sorting
    results_sorted = run_screening_strategy(
        MockStrategy,
        ticker_list=["AAPL"],
        sorting_key=lambda x: x['ticker']
    )
    assert len(results_sorted) == 1
