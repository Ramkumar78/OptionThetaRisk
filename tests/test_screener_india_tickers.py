import pytest
from option_auditor.screener import get_indian_tickers

def test_get_indian_tickers_count():
    """Verify that we are getting approximately 500 tickers."""
    tickers = get_indian_tickers()
    # We expect roughly 500. The list might have slightly less due to duplicate removal or more if updated.
    # The list I pasted had ~480-500 lines.
    # Let's assert > 400 to be safe and meaningful.
    assert len(tickers) > 400, f"Expected > 400 tickers, got {len(tickers)}"

def test_get_indian_tickers_format():
    """Verify that all tickers end with .NS."""
    tickers = get_indian_tickers()
    for ticker in tickers:
        assert ticker.endswith(".NS"), f"Ticker {ticker} does not end with .NS"

def test_get_indian_tickers_content():
    """Verify some known heavyweights are present."""
    tickers = get_indian_tickers()
    known_bluechips = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
    for chip in known_bluechips:
        assert chip in tickers, f"Expected {chip} to be in the list"
