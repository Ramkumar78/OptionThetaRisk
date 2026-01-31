import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import fetch_batch_data_safe

# Mock Data Generator
def create_mock_batch(tickers):
    # Creates a MultiIndex DF mimicking yfinance
    # yfinance returns (Price, Ticker) or (Ticker, Price).
    # Usually MultiIndex columns: Level 0 = Ticker, Level 1 = Price Type (with group_by='ticker')
    # Let's adjust mock to match group_by='ticker' structure
    cols = pd.MultiIndex.from_product([tickers, ['Close', 'Open', 'High', 'Low', 'Volume']])
    df = pd.DataFrame(100.0, index=[0, 1], columns=cols)
    return df

def test_batch_fetching_logic():
    """
    Verifies that a large list is split into chunks and reassembled.
    """
    # Create a list of 150 dummy tickers
    tickers = [f"SYM{i}" for i in range(150)]

    with patch('yfinance.download') as mock_download:
        # Scenario:
        # yf.download is called multiple times.
        # We verify it is called with chunks, not the whole list.

        mock_download.side_effect = lambda t, **kwargs: create_mock_batch(t)

        result = fetch_batch_data_safe(tickers, chunk_size=50)

        # 1. Verify Result is not empty
        assert not result.empty

        # 2. Verify Result contains all tickers (150 tickers * 5 columns = 750 cols)
        # Note: Depending on mock structure, checking shape or columns
        assert len(result.columns.levels[0]) == 150

        # 3. Verify chunking occurred (150 / 50 = 3 calls)
        assert mock_download.call_count == 3

        # Check call args to ensure no list was > 50
        for call in mock_download.call_args_list:
            args, _ = call
            batch_requested = args[0]
            assert len(batch_requested) <= 50

def test_partial_failure_resilience():
    """
    Verifies that if one batch fails (throws error), others are still returned.
    """
    tickers = ["A", "B", "C", "D"]

    with patch('yfinance.download') as mock_download:
        def side_effect(t_list, **kwargs):
            if "A" in t_list:
                raise Exception("API Timeout")
            return create_mock_batch(t_list)

        mock_download.side_effect = side_effect

        # Force chunk size 2: [A, B] fails, [C, D] succeeds
        result = fetch_batch_data_safe(tickers, chunk_size=2)

        # Should return C and D, but not crash
        assert not result.empty
        assert "C" in result.columns.levels[0]
        assert "A" not in result.columns.levels[0]
