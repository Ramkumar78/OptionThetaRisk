import os
import pytest
from unittest.mock import patch
from option_auditor.us_stock_data import get_united_states_stocks

@patch('option_auditor.us_stock_data.load_tickers_from_csv')
def test_get_united_states_stocks(mock_load):
    # Mock return value
    mock_load.return_value = ["AAPL", "GOOG"]

    result = get_united_states_stocks()

    assert result == ["AAPL", "GOOG"]

    # Check that it called load_tickers_from_csv with the correct path
    args, kwargs = mock_load.call_args
    file_path = args[0]

    # Verify path ends with us_sectors.csv
    assert file_path.endswith("us_sectors.csv")
    assert "option_auditor" in file_path
    assert "data" in file_path

    # Verify column name was passed
    assert kwargs['column_name'] == 'Symbol'
