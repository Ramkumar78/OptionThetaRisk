import pytest
import pandas as pd
from datetime import datetime
from option_auditor.parsers import IBKRParser

@pytest.fixture
def parser():
    return IBKRParser()

def test_ibkr_parser_loose_columns(parser):
    """Test loose match column identification (e.g., 'T. Price' vs 'TradePrice')."""

    # Case 1: Standard columns
    df1 = pd.DataFrame({
        "Symbol": ["AAPL"],
        "Date/Time": ["2023-10-27 10:00:00"],
        "Quantity": [10],
        "T. Price": [150.0],
        "Comm/Fee": [1.0],
        "AssetClass": ["STK"]
    })

    # Case 2: Alternative columns
    df2 = pd.DataFrame({
        "UnderlyingSymbol": ["AAPL"],
        "TradeDate": ["2023-10-27 10:00:00"],
        "Qty": [10],
        "TradePrice": [150.0],
        "Commission": [1.0],
        "Asset Class": ["STK"]
    })

    result1 = parser.parse(df1)
    result2 = parser.parse(df2)

    assert not result1.empty
    assert not result2.empty
    assert result1.iloc[0]["proceeds"] == result2.iloc[0]["proceeds"]
    assert result1.iloc[0]["fees"] == result2.iloc[0]["fees"]
    assert result1.iloc[0]["symbol"] == "AAPL"
    assert result2.iloc[0]["symbol"] == "AAPL"

def test_ibkr_parser_custom_datetime(parser):
    """Verify custom IBKR datetime parsing (the YYYYMMDD;HHMMSS format)."""

    df = pd.DataFrame({
        "Symbol": ["AAPL"],
        "Date/Time": ["20231027;103000"],
        "Quantity": [100],
        "T. Price": [150.0],
        "Comm/Fee": [1.0],
        "AssetClass": ["STK"]
    })

    result = parser.parse(df)

    assert not result.empty
    dt = result.iloc[0]["datetime"]
    assert isinstance(dt, datetime)
    assert dt.year == 2023
    assert dt.month == 10
    assert dt.day == 27
    assert dt.hour == 10
    assert dt.minute == 30
    assert dt.second == 0

def test_ibkr_parser_asset_inference(parser):
    """Test asset class detection (STK vs OPT) when the explicit column is missing."""

    # DataFrame without 'AssetClass'
    df = pd.DataFrame({
        "Symbol": ["AAPL", "GOOG"],
        "Date/Time": ["2023-10-27 10:00:00", "2023-10-27 10:00:00"],
        "Quantity": [100, 1],
        "T. Price": [150.0, 5.0],
        "Comm/Fee": [1.0, 1.0],
        # 'Put/Call' implies OPT if C or P
        "Put/Call": ["", "C"],
        "Expiry": ["", "20231117"],
        "Strike": ["", "150"]
    })

    result = parser.parse(df)

    assert len(result) == 2

    # First row: No Put/Call -> inferred as STOCK
    row1 = result.iloc[0]
    assert row1["asset_type"] == "STOCK"
    assert row1["symbol"] == "AAPL"

    # Second row: Put/Call is 'C' -> inferred as OPT
    row2 = result.iloc[1]
    assert row2["asset_type"] == "OPT"
    assert row2["symbol"] == "GOOG"
    assert row2["right"] == "C"

def test_ibkr_parser_proceeds_fees(parser):
    """Ensure proceeds and fees are calculated correctly for both Long and Short positions."""

    # 1. Long Stock: Buy 10 @ 100. Proceeds = -10 * 100 * 1 = -1000. Fees = 1.
    # 2. Short Stock: Sell 10 @ 100. Qty = -10. Proceeds = -(-10) * 100 * 1 = 1000. Fees = 1.
    # 3. Long Option: Buy 1 @ 5.0. Proceeds = -1 * 5.0 * 100 = -500. Fees = 1.
    # 4. Short Option: Sell 1 @ 5.0. Qty = -1. Proceeds = -(-1) * 5.0 * 100 = 500. Fees = 1.

    df = pd.DataFrame({
        "Symbol": ["S1", "S2", "O1", "O2"],
        "Date/Time": ["2023-10-27 10:00:00"] * 4,
        "Quantity": [10, -10, 1, -1],
        "T. Price": [100.0, 100.0, 5.0, 5.0],
        "Comm/Fee": [-1.0, -1.0, -1.0, -1.0], # IBKR reports fees as negative usually, parser takes abs()
        "AssetClass": ["STK", "STK", "OPT", "OPT"],
        "Put/Call": ["", "", "C", "P"],
        "Expiry": ["", "", "20231117", "20231117"],
        "Strike": ["", "", "100", "100"]
    })

    result = parser.parse(df)

    # Check Long Stock
    r1 = result[result["symbol"] == "S1"].iloc[0]
    assert r1["qty"] == 10
    assert r1["proceeds"] == -1000.0
    assert r1["fees"] == 1.0

    # Check Short Stock
    r2 = result[result["symbol"] == "S2"].iloc[0]
    assert r2["qty"] == -10
    assert r2["proceeds"] == 1000.0
    assert r2["fees"] == 1.0

    # Check Long Option
    r3 = result[result["symbol"] == "O1"].iloc[0]
    assert r3["qty"] == 1
    assert r3["proceeds"] == -500.0
    assert r3["fees"] == 1.0

    # Check Short Option
    r4 = result[result["symbol"] == "O2"].iloc[0]
    assert r4["qty"] == -1
    assert r4["proceeds"] == 500.0
    assert r4["fees"] == 1.0

def test_ibkr_parser_zero_quantity(parser):
    """Include an edge case for '0 quantity' rows."""

    df = pd.DataFrame({
        "Symbol": ["AAPL", "GOOG"],
        "Date/Time": ["2023-10-27 10:00:00", "2023-10-27 10:05:00"],
        "Quantity": [10, 0],
        "T. Price": [150.0, 0.0],
        "Comm/Fee": [1.0, 0.0],
        "AssetClass": ["STK", "STK"]
    })

    result = parser.parse(df)

    # Should only have 1 row (AAPL)
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "AAPL"
