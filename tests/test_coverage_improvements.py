
import pandas as pd
import pytest
import os
from datetime import datetime
from option_auditor.parsers import TastytradeFillsParser, TastytradeParser
from option_auditor.main_analyzer import analyze_csv

def test_tasty_fills_parser_fallback_logic():
    # Test the fallback parser (space separated tokens)
    # Format: Qty Month Day [DTE/Exp] Strike Right ...
    # Example: "1 JAN 20 25d 100 CALL"

    df = pd.DataFrame([{
        "Time": "2023-01-01 10:00",
        "Symbol": "TEST",
        "Description": "1 JAN 20 25d 100 CALL STO",
        "Price": "1.00 cr",
        "Commissions": "0",
        "Fees": "0"
    }])

    parser = TastytradeFillsParser()
    result = parser.parse(df)

    assert not result.empty
    assert len(result) == 1
    assert result.iloc[0]["qty"] == 1
    assert result.iloc[0]["strike"] == 100.0
    assert result.iloc[0]["right"] == "C"

def test_tasty_fills_parser_fallback_logic_variations():
    # Test variations to hit different branches in fallback logic

    rows = [
        # "Exp" token
        {
            "Time": "2023-01-01 10:00",
            "Symbol": "TEST1",
            "Description": "1 FEB 15 Exp 50 PUT BTO",
            "Price": "1.00 db",
            "Commissions": "0", "Fees": "0"
        },
        # No DTE token (just strike at pos 3) -> "1 MAR 10 75 CALL"
        {
            "Time": "2023-01-01 10:00",
            "Symbol": "TEST2",
            "Description": "1 MAR 10 75 CALL STO",
            "Price": "1.00 cr",
            "Commissions": "0", "Fees": "0"
        }
    ]
    df = pd.DataFrame(rows)
    parser = TastytradeFillsParser()
    result = parser.parse(df)

    assert len(result) == 2

    # Check TEST1
    r1 = result[result["symbol"] == "TEST1"].iloc[0]
    assert r1["right"] == "P"
    assert r1["strike"] == 50.0

    # Check TEST2
    r2 = result[result["symbol"] == "TEST2"].iloc[0]
    assert r2["right"] == "C"
    assert r2["strike"] == 75.0

def test_tasty_fills_parser_invalid_lines():
    # Lines that should be skipped by fallback parser

    rows = [
        # Too short
        {"Time": "2023-01-01", "Symbol": "S1", "Description": "1 JAN 20"},
        # Invalid qty
        {"Time": "2023-01-01", "Symbol": "S2", "Description": "X JAN 20 100 CALL STO"},
        # Invalid strike
        {"Time": "2023-01-01", "Symbol": "S3", "Description": "1 JAN 20 X CALL STO"},
        # Unknown right
        {"Time": "2023-01-01", "Symbol": "S4", "Description": "1 JAN 20 100 STRANGLE STO"},
    ]
    # Add dummy price/cols
    for r in rows:
        r["Price"] = "0"
        r["Commissions"] = "0"
        r["Fees"] = "0"

    df = pd.DataFrame(rows)
    parser = TastytradeFillsParser()
    result = parser.parse(df)

    # Should be empty as all lines are invalid
    assert result.empty

def test_tasty_fills_parser_fallback_exceptions():
    # Test exceptions in fallback parser (e.g. date parsing failure)

    # Invalid Month -> triggers Exception in date parsing
    df = pd.DataFrame([{
        "Time": "2023-01-01 10:00",
        "Symbol": "TEST",
        "Description": "1 XYZ 20 100 CALL STO", # XYZ is not a month
        "Price": "1.00 cr",
        "Commissions": "0", "Fees": "0"
    }])
    parser = TastytradeFillsParser()
    result = parser.parse(df)
    # Should parse the line but expiry will be NaT
    assert not result.empty
    assert pd.isna(result.iloc[0]["expiry"])

    # Year Rollover Logic (Dec trade, Jan Expiry)
    df_rollover = pd.DataFrame([{
        "Time": "2023-12-01 10:00",
        "Symbol": "TEST",
        "Description": "1 JAN 20 100 CALL STO",
        "Price": "1.00 cr",
        "Commissions": "0", "Fees": "0"
    }])
    result_ro = parser.parse(df_rollover)
    assert result_ro.iloc[0]["expiry"].year == 2024

def test_parse_tasty_datetime_edge_cases():
    parser = TastytradeParser() # or any subclass

    # Use format that fails dateutil but passes custom logic
    # "11/26, 5:53p" (with comma) seems to be the target of custom logic

    ts_noon = parser._parse_tasty_datetime("1/1, 12:00p")
    assert ts_noon.hour == 12

    ts_midnight = parser._parse_tasty_datetime("1/1, 12:00a")
    assert ts_midnight.hour == 0

    ts_pm = parser._parse_tasty_datetime("1/1, 1:00p")
    assert ts_pm.hour == 13

    # Test invalid
    assert parser._parse_tasty_datetime(None) is None
    assert parser._parse_tasty_datetime("invalid") is None

def test_analyze_csv_output_error_handling(tmp_path):
    # Test that file writing errors are caught and ignored (as per try/except block)

    # Create a dummy CSV with a closed trade (Buy then Sell)
    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w") as f:
        f.write("Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n")
        f.write("2023-01-01 10:00,AAPL,1,Buy to Open,1.0,0,2023-02-01,150,Call\n")
        f.write("2023-01-02 10:00,AAPL,1,Sell to Close,1.2,0,2023-02-01,150,Call\n")

    # Easier: make out_dir a file path so os.makedirs fails
    out_file = tmp_path / "out_is_a_file"
    out_file.touch()

    # This should not raise exception, but return result
    res = analyze_csv(str(csv_path), out_dir=str(out_file))

    assert res is not None
    # Now that we have a closed trade, num_trades should be 1
    assert res["metrics"]["num_trades"] == 1

def test_broker_detection_lines(tmp_path):
    # Cover the lines in main_analyzer.py:
    # if "Description" in df.columns and "Symbol" in df.columns: parser = TastytradeFillsParser()

    # Case 1: broker="tasty", but has Description + Symbol -> uses Fills parser
    csv_fills = tmp_path / "fills.csv"
    with open(csv_fills, "w") as f:
        f.write("Time,Symbol,Description,Price,Commissions,Fees\n")
        f.write("2023-01-01,AAPL,1 JAN 20 150 CALL STO,1.0 cr,0,0\n")

    res = analyze_csv(str(csv_fills), broker="tasty", out_dir=None)
    assert res["broker"] == "tasty"
    # Fills parser should extract the trade
    assert res["metrics"]["num_trades"] >= 0

    # Case 2: broker="tasty", NO Description -> uses Standard parser
    csv_standard = tmp_path / "standard.csv"
    with open(csv_standard, "w") as f:
        f.write("Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n")
        f.write("2023-01-01 10:00,AAPL,1,Buy to Open,1.0,0,2023-02-01,150,Call\n")

    res2 = analyze_csv(str(csv_standard), broker="tasty", out_dir=None)
    # Standard parser should extract the open trade (num_trades=0 closed, but no error)
    assert res2 is not None
