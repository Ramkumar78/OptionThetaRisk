import pytest
import pandas as pd
from io import StringIO
from option_auditor.parsers import IBKRParser
from option_auditor.main_analyzer import analyze_csv

# Synthetic IBKR Flex Query CSV Data
IBKR_CSV_CONTENT = """ClientAccountID,Currency,Symbol,DateTime,Quantity,T. Price,Proceeds,Comm/Fee,Multiplier,Strike,Expiry,Put/Call,AssetClass,Code
U123456,USD,SPY,20231025;103000,1,1.50,-150.00,-1.00,100,420,20231027,P,OPT,O
U123456,USD,SPY,20231026;140000,-1,0.50,50.00,-1.00,100,420,20231027,P,OPT,C
U123456,USD,AAPL,20231001;093500,-1,2.00,200.00,-1.05,100,150,20231117,C,OPT,O
"""

def test_ibkr_parser_direct():
    df = pd.read_csv(StringIO(IBKR_CSV_CONTENT))
    parser = IBKRParser()
    norm = parser.parse(df)

    assert len(norm) == 3

    # Check Row 1: Long Put
    # Qty 1 -> Long (+1)
    # Price 1.50 -> Proceeds -150.00
    # Fees -1.00 -> 1.00
    row1 = norm.iloc[0]
    assert row1["symbol"] == "SPY"
    assert row1["qty"] == 1.0
    assert row1["proceeds"] == -150.0
    assert row1["fees"] == 1.0
    assert row1["strike"] == 420.0
    assert row1["right"] == "P"
    assert row1["expiry"].strftime("%Y-%m-%d") == "2023-10-27"
    assert row1["datetime"].strftime("%Y-%m-%d %H:%M:%S") == "2023-10-25 10:30:00"

    # Check Row 2: Close Short Put (Actually it was Long Put closed by Sell)
    # CSV says Quantity -1 (Sell), Proceeds 50.00.
    row2 = norm.iloc[1]
    assert row2["symbol"] == "SPY"
    assert row2["qty"] == -1.0
    assert row2["proceeds"] == 50.0
    assert row2["fees"] == 1.0

    # Check Row 3: Short Call
    # Qty -1 -> Short (-1)
    # Proceeds 200.00
    row3 = norm.iloc[2]
    assert row3["symbol"] == "AAPL"
    assert row3["qty"] == -1.0
    assert row3["proceeds"] == 200.0
    assert row3["fees"] == 1.05
    assert row3["strike"] == 150.0
    assert row3["right"] == "C"

def test_ibkr_integration_auto_detect(tmp_path):
    f = tmp_path / "ibkr_test.csv"
    f.write_text(IBKR_CSV_CONTENT)

    # Analyze with auto detection
    res = analyze_csv(csv_path=str(f), broker="auto")
    assert "error" not in res, f"Analysis failed: {res.get('error')}"
    assert res["broker"] == "ibkr"
    assert res["metrics"]["num_trades"] > 0
    assert len(res["strategy_groups"]) > 0

def test_ibkr_integration_explicit(tmp_path):
    f = tmp_path / "ibkr_test.csv"
    f.write_text(IBKR_CSV_CONTENT)

    # Analyze with explicit broker
    res = analyze_csv(csv_path=str(f), broker="ibkr")
    assert "error" not in res
    assert res["broker"] == "ibkr"

def test_ibkr_parser_iso_dates():
    # Test fallback to dateutil parser (no semicolons)
    csv_content = """ClientAccountID,Currency,Symbol,DateTime,Quantity,T. Price,Proceeds,Comm/Fee,Multiplier,Strike,Expiry,Put/Call,AssetClass,Code
U123456,USD,SPY,2023-10-25 10:30:00,1,1.50,-150.00,-1.00,100,420,2023-10-27,P,OPT,O
"""
    df = pd.read_csv(StringIO(csv_content))
    parser = IBKRParser()
    norm = parser.parse(df)

    assert len(norm) == 1
    row = norm.iloc[0]
    assert row["datetime"].strftime("%Y-%m-%d %H:%M:%S") == "2023-10-25 10:30:00"
    assert row["expiry"].strftime("%Y-%m-%d") == "2023-10-27"
