import os
import pytest
import pandas as pd
from unittest.mock import patch, mock_open
from option_auditor.common.file_utils import load_tickers_from_csv

# Sample CSV data
CSV_WITH_HEADER = "Symbol,Company\nAAPL,Apple\nMSFT,Microsoft\nnan,Unknown\n"
CSV_NO_HEADER = "AAPL\nMSFT\nnan\n"
CSV_WRONG_HEADER = "Ticker,Name\nAAPL,Apple\n"
CSV_EMPTY = ""

@pytest.fixture
def mock_exists():
    with patch("os.path.exists") as m:
        yield m

def test_file_not_found(mock_exists):
    mock_exists.return_value = False
    result = load_tickers_from_csv("non_existent.csv")
    assert result == []

def test_load_with_header_success(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv") as mock_read:
        # Mock DataFrame
        mock_read.return_value = pd.DataFrame({'Symbol': ['AAPL', 'MSFT', 'nan']})

        result = load_tickers_from_csv("test.csv", column_name="Symbol")
        assert result == ["AAPL", "MSFT"]

def test_load_with_header_missing_column(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv") as mock_read:
        # DF without target column
        mock_read.return_value = pd.DataFrame({'Other': ['AAPL']})

        result = load_tickers_from_csv("test.csv", column_name="Symbol")
        assert result == []

def test_load_no_header_success(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv") as mock_read:
        # DF from no-header CSV (default col 0)
        mock_read.return_value = pd.DataFrame({0: ['AAPL', 'MSFT', 'nan']})

        result = load_tickers_from_csv("test.csv")
        assert result == ["AAPL", "MSFT"]

def test_load_empty_file(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv") as mock_read:
        mock_read.return_value = pd.DataFrame()

        result = load_tickers_from_csv("test.csv")
        assert result == []

def test_load_exception(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv", side_effect=Exception("Disk Error")):
        result = load_tickers_from_csv("test.csv")
        assert result == []

def test_ignore_list(mock_exists):
    mock_exists.return_value = True
    with patch("pandas.read_csv") as mock_read:
        # Symbols to ignore
        data = ['AAPL', 'symbol', 'ticker', 'company', 'nan', '/ES']
        mock_read.return_value = pd.DataFrame({0: data})

        result = load_tickers_from_csv("test.csv")
        assert result == ["AAPL"]
