import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import (
    get_currency_symbol,
    fetch_exchange_rate,
    convert_currency,
    get_market_holidays,
    _calculate_trend_breakout_date,
    fetch_batch_data_safe,
    prepare_data_for_ticker
)
from option_auditor.common.price_utils import (
    normalize_ticker,
    fetch_live_prices
)

def test_get_currency_symbol():
    """Test mapping of broker symbols to currency codes."""
    assert get_currency_symbol("TSLA.L") == "GBP"
    assert get_currency_symbol("INFY.NS") == "INR"
    assert get_currency_symbol("RELIANCE.BO") == "INR"
    assert get_currency_symbol("AIR.PA") == "EUR"
    assert get_currency_symbol("SIE.DE") == "EUR"
    assert get_currency_symbol("TSLA") == "USD"
    assert get_currency_symbol("") == "USD"
    assert get_currency_symbol(None) == "USD"

def test_fetch_exchange_rate_same_currency():
    """Test same currency returns 1.0."""
    assert fetch_exchange_rate("USD", "USD") == 1.0
    assert fetch_exchange_rate("GBP", "gbp") == 1.0

@patch("yfinance.Ticker")
def test_fetch_exchange_rate_mocked(mock_ticker):
    """Test fetching live rate from yfinance."""
    mock_instance = MagicMock()
    mock_ticker.return_value = mock_instance

    # Mock successful history
    mock_hist = pd.DataFrame({"Close": [1.25]}, index=[pd.Timestamp("2024-01-01")])
    mock_instance.history.return_value = mock_hist

    rate = fetch_exchange_rate("GBP", "USD")
    assert rate == 1.25
    mock_ticker.assert_called_with("GBPUSD=X")

@patch("yfinance.Ticker")
def test_fetch_exchange_rate_fallback(mock_ticker):
    """Test fallback when yfinance fails."""
    mock_instance = MagicMock()
    mock_ticker.return_value = mock_instance

    # Mock failure (empty dataframe)
    mock_instance.history.return_value = pd.DataFrame()

    # Should use FALLBACK_RATES for GBP/USD (approx 1.27)
    rate = fetch_exchange_rate("GBP", "USD")
    assert 1.20 < rate < 1.35

    # Test inverse fallback
    rate_inv = fetch_exchange_rate("USD", "GBP")
    assert 0.7 < rate_inv < 0.85

def test_convert_currency():
    """Test currency conversion calculation."""
    with patch("option_auditor.common.data_utils.fetch_exchange_rate") as mock_rate:
        mock_rate.return_value = 1.5
        converted = convert_currency(100, "GBP", "USD")
        assert converted == 150.0

def test_get_market_holidays():
    """Test holiday lists for supported exchanges."""
    nyse_holidays = get_market_holidays("NYSE")
    assert len(nyse_holidays) > 0
    assert date(2024, 12, 25) in nyse_holidays

    lse_holidays = get_market_holidays("LSE")
    assert len(lse_holidays) > 0
    assert date(2024, 12, 26) in lse_holidays # Boxing Day

    nse_holidays = get_market_holidays("NSE")
    assert len(nse_holidays) > 0

    # Test case insensitivity
    assert get_market_holidays("nyse") == nyse_holidays

def test_calculate_trend_breakout_date_insufficient_data():
    """Test returns N/A for short dataframes."""
    df = pd.DataFrame({"Close": [100] * 40})
    assert _calculate_trend_breakout_date(df) == "N/A"
    assert _calculate_trend_breakout_date(pd.DataFrame()) == "N/A"

def test_calculate_trend_breakout_date_no_trend():
    """Test returns N/A when trend is broken (Close <= 20d Low)."""
    # Create sufficient data
    dates = pd.date_range(start="2023-01-01", periods=100)
    df = pd.DataFrame(index=dates)
    df["Close"] = 100.0
    df["High"] = 105.0
    df["Low"] = 95.0

    # Force trend break at the end
    df.loc[df.index[-1], "Close"] = 90.0 # Below previous lows

    breakout = _calculate_trend_breakout_date(df)
    assert breakout == "N/A"

def test_calculate_trend_breakout_date_valid_trend():
    """Test returns date when breakout > 50d High occurred."""
    dates = pd.date_range(start="2023-01-01", periods=100)
    df = pd.DataFrame(index=dates)
    # Flat market first
    df["Close"] = 100.0
    df["High"] = 102.0
    df["Low"] = 98.0

    # Breakout at index 80
    breakout_date = dates[80]
    df.loc[dates[80]:, "Close"] = 110.0 # Jump up
    df.loc[dates[80]:, "High"] = 112.0
    df.loc[dates[80]:, "Low"] = 108.0 # Above previous lows

    # Calculate expected columns manually to ensure test validity
    # High_50 will be 102 until index 80+
    # Low_20 will be 98 until index 80+

    res = _calculate_trend_breakout_date(df)
    assert res == breakout_date.strftime("%Y-%m-%d")

@patch("option_auditor.common.data_utils.yf.download")
def test_fetch_batch_data_safe(mock_download):
    """Test batch fetching with chunking."""
    tickers = [f"T{i}" for i in range(35)] # More than chunk_size 30

    # Mock return for each chunk
    # Chunk 1: 30 tickers
    # Chunk 2: 5 tickers

    df1 = pd.DataFrame({"Close": [100]}, index=[pd.Timestamp("2024-01-01")])
    df2 = pd.DataFrame({"Close": [100]}, index=[pd.Timestamp("2024-01-01")])

    # Use side_effect to return different dfs for calls
    mock_download.side_effect = [df1, df2]

    res = fetch_batch_data_safe(tickers, chunk_size=30)

    assert mock_download.call_count == 2
    assert not res.empty

def test_fetch_batch_data_empty():
    """Test empty ticker list returns empty DataFrame."""
    assert fetch_batch_data_safe([]).empty

@patch("option_auditor.common.data_utils.yf.download")
def test_fetch_batch_data_exception(mock_download):
    """Test exception handling during download."""
    mock_download.side_effect = Exception("Network Error")

    # Should catch and log, returning empty or partial
    res = fetch_batch_data_safe(["AAPL"])
    assert res.empty

def test_prepare_data_for_ticker_from_batch():
    """Test extracting specific ticker data from batch result."""
    dates = pd.date_range(start="2023-01-01", periods=5)

    # Create MultiIndex DataFrame: (Ticker, Price)
    # fetch_batch_data_safe returns columns like (Price, Ticker) or (Ticker, Price) depending on version/args
    # data_utils.py says: group_by='ticker' -> Level 0 is Ticker

    cols = pd.MultiIndex.from_product([["AAPL", "MSFT"], ["Open", "High", "Low", "Close", "Volume"]])
    df = pd.DataFrame(np.random.randn(5, 10), index=dates, columns=cols)

    # Test extraction
    res = prepare_data_for_ticker("AAPL", df, None, "1y", "1d", None, False)

    assert res is not None
    assert "Close" in res.columns
    assert isinstance(res.columns, pd.Index) # Should be flattened
    assert not isinstance(res.columns, pd.MultiIndex)
    assert len(res) == 5

@patch("option_auditor.common.data_utils.fetch_data_with_retry")
def test_prepare_data_for_ticker_fallback(mock_fetch):
    """Test fetching single ticker when not in batch."""
    mock_fetch.return_value = pd.DataFrame({
        "Open": [100], "High": [110], "Low": [90], "Close": [105], "Volume": [1000]
    }, index=[pd.Timestamp("2024-01-01")])

    res = prepare_data_for_ticker("GOOG", None, None, "1y", "1d", None, False)

    mock_fetch.assert_called_once()
    assert res is not None
    assert res["Close"].iloc[0] == 105


def test_normalize_ticker():
    """Test ticker normalization logic."""
    assert normalize_ticker("SPX") == "^SPX"
    assert normalize_ticker("VIX") == "^VIX"
    assert normalize_ticker("/ES") == "ES=F"
    assert normalize_ticker("/CL") == "CL=F"
    assert normalize_ticker("BRK/B") == "BRK-B"
    assert normalize_ticker("AAPL") == "AAPL"

    # Edge cases
    assert normalize_ticker(None) == "None"
    assert normalize_ticker(123) == "123"

@patch("option_auditor.common.price_utils.yf.download")
def test_fetch_live_prices_batch(mock_download):
    """Test fetching live prices for multiple symbols."""
    # Mock return DataFrame for multiple tickers
    # yfinance returns MultiIndex if >1 ticker
    cols = pd.MultiIndex.from_product([["AAPL", "GOOG"], ["Open", "High", "Low", "Close", "Volume"]])
    df = pd.DataFrame([[150, 155, 145, 150, 1000, 2800, 2850, 2750, 2800, 500]], columns=cols, index=[pd.Timestamp.now()])

    mock_download.return_value = df

    prices = fetch_live_prices(["AAPL", "GOOG"])

    assert prices["AAPL"] == 150.0
    assert prices["GOOG"] == 2800.0

@patch("option_auditor.common.price_utils.yf.download")
def test_fetch_live_prices_single(mock_download):
    """Test fetching live price for a single symbol."""
    # yfinance returns simple DataFrame for single ticker
    df = pd.DataFrame({"Close": [150.0]}, index=[pd.Timestamp.now()])

    mock_download.return_value = df

    prices = fetch_live_prices(["AAPL"])

    assert prices["AAPL"] == 150.0

@patch("option_auditor.common.price_utils.yf.Ticker")
@patch("option_auditor.common.price_utils.yf.download")
def test_fetch_live_prices_fallback(mock_download, mock_ticker):
    """Test fallback to individual fetch if batch misses."""
    # Batch returns empty or missing specific symbol
    mock_download.return_value = pd.DataFrame() # Batch fails

    # Mock individual Ticker
    mock_instance = MagicMock()
    mock_ticker.return_value = mock_instance

    # Mock fast_info
    mock_instance.fast_info = {"last_price": 160.0}

    prices = fetch_live_prices(["MSFT"])

    assert prices["MSFT"] == 160.0
    mock_ticker.assert_called_with("MSFT")
