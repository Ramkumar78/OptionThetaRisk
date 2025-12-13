import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from option_auditor.common.data_utils import fetch_batch_data_safe

def mock_yf_response(tickers, **kwargs):
    """
    Creates a fake MultiIndex DF structure that yfinance returns.
    """
    if isinstance(tickers, str):
        tickers = [tickers]

    # Check if 'Close' is needed? yf.download normally returns OHLCV.
    # We construct a multiindex (Ticker, PriceType) because group_by='ticker' is default in fetch_batch
    # Actually wait, yfinance with group_by='ticker' returns Level 0 as Ticker.

    cols = pd.MultiIndex.from_product([tickers, ['Close', 'Open', 'High', 'Low', 'Volume', 'Adj Close']])
    data = pd.DataFrame(100.0, index=pd.date_range("2023-01-01", periods=10), columns=cols)
    return data

def test_fetch_batch_chunks_requests():
    """Ensure we split 150 tickers into 3 requests of 50"""
    tickers = [f"TICK{i}" for i in range(150)]

    with patch('yfinance.download') as mock_download:
        mock_download.side_effect = lambda t, **k: mock_yf_response(t, **k)

        df = fetch_batch_data_safe(tickers, chunk_size=50)

        # Verify result structure
        assert not df.empty
        # Check that we have 150 tickers in top level columns
        # Depending on how concatenation happens.
        # If all successful, we should see 150 unique level 0 columns.
        assert len(df.columns.levels[0]) == 150

        # Verify Logic: Should be called 3 times (150 / 50)
        assert mock_download.call_count == 3

def test_fetch_handles_partial_failure():
    """Ensure one bad batch doesn't kill the whole process"""
    tickers = ["AAPL", "GOOG", "BAD_BATCH_TICKER", "MSFT"]

    with patch('yfinance.download') as mock_download:
        def side_effect(chunk, **kwargs):
            if "BAD_BATCH_TICKER" in chunk:
                raise Exception("API Timeout")
            return mock_yf_response(chunk)

        mock_download.side_effect = side_effect

        # Force small chunk size to isolate the bad ticker
        # Chunks: [AAPL, GOOG] (size 2), [BAD..., MSFT] (size 2)
        # Note: 'tickers' list is unordered set inside function due to list(set(...))?
        # Actually set() ruins order. But fetch_batch_data_safe does list(set(tickers)).
        # So we can't guarantee chunk content perfectly unless we force deduplication to result in same list.
        # Let's assume input has no dupes.

        # To make test deterministic with chunk content, we need to know the order after set().
        # But for this test, we just check that we get SOME result back despite 1 failure.

        df = fetch_batch_data_safe(tickers, chunk_size=2)

        # Result should not be empty (unless all chunks failed)
        # With 4 tickers and chunk size 2, we have 2 chunks.
        # If one chunk contains BAD_BATCH_TICKER, it fails. The other chunk should succeed.
        # So we expect 2 tickers in result.

        assert not df.empty
        assert len(df.columns.levels[0]) >= 1

def test_fetch_handles_total_failure():
    """Ensure graceful return on 100% failure"""
    tickers = ["FAIL1", "FAIL2"]

    with patch('yfinance.download') as mock_download:
        mock_download.side_effect = Exception("All down")

        df = fetch_batch_data_safe(tickers, chunk_size=2)

        assert df.empty
        assert isinstance(df, pd.DataFrame)
