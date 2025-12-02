import pandas as pd
import pytest
import io
from option_auditor.parsers import TastytradeFillsParser, TastytradeParser
from option_auditor.main_analyzer import analyze_csv

def test_tasty_fills_parser_fallback_logic():
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
    rows = [
        {"Time": "2023-01-01 10:00", "Symbol": "TEST1", "Description": "1 FEB 15 Exp 50 PUT BTO", "Price": "1.00 db", "Commissions": "0", "Fees": "0"},
        {"Time": "2023-01-01 10:00", "Symbol": "TEST2", "Description": "1 MAR 10 75 CALL STO", "Price": "1.00 cr", "Commissions": "0", "Fees": "0"}
    ]
    df = pd.DataFrame(rows)
    parser = TastytradeFillsParser()
    result = parser.parse(df)
    assert len(result) == 2
    r1 = result[result["symbol"] == "TEST1"].iloc[0]
    assert r1["right"] == "P"
    assert r1["strike"] == 50.0
    r2 = result[result["symbol"] == "TEST2"].iloc[0]
    assert r2["right"] == "C"
    assert r2["strike"] == 75.0

def test_tasty_fills_parser_invalid_lines():
    rows = [
        {"Time": "2023-01-01", "Symbol": "S1", "Description": "1 JAN 20"},
        {"Time": "2023-01-01", "Symbol": "S2", "Description": "X JAN 20 100 CALL STO"},
        {"Time": "2023-01-01", "Symbol": "S3", "Description": "1 JAN 20 X CALL STO"},
        {"Time": "2023-01-01", "Symbol": "S4", "Description": "1 JAN 20 100 STRANGLE STO"},
    ]
    for r in rows:
        r["Price"] = "0"
        r["Commissions"] = "0"
        r["Fees"] = "0"
    df = pd.DataFrame(rows)
    parser = TastytradeFillsParser()
    result = parser.parse(df)
    assert result.empty

def test_tasty_fills_parser_fallback_exceptions():
    df = pd.DataFrame([{"Time": "2023-01-01 10:00", "Symbol": "TEST", "Description": "1 XYZ 20 100 CALL STO", "Price": "1.00 cr", "Commissions": "0", "Fees": "0"}])
    parser = TastytradeFillsParser()
    result = parser.parse(df)
    assert not result.empty
    assert pd.isna(result.iloc[0]["expiry"])

    df_rollover = pd.DataFrame([{"Time": "2023-12-01 10:00", "Symbol": "TEST", "Description": "1 JAN 20 100 CALL STO", "Price": "1.00 cr", "Commissions": "0", "Fees": "0"}])
    result_ro = parser.parse(df_rollover)
    assert result_ro.iloc[0]["expiry"].year == 2024

def test_parse_tasty_datetime_edge_cases():
    parser = TastytradeParser()
    ts_noon = parser._parse_tasty_datetime("1/1, 12:00p")
    assert ts_noon.hour == 12
    ts_midnight = parser._parse_tasty_datetime("1/1, 12:00a")
    assert ts_midnight.hour == 0
    ts_pm = parser._parse_tasty_datetime("1/1, 1:00p")
    assert ts_pm.hour == 13
    assert parser._parse_tasty_datetime(None) is None
    assert parser._parse_tasty_datetime("invalid") is None

def test_analyze_csv_output_error_handling():
    csv_content = "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n" \
                  "2023-01-01 10:00,AAPL,1,Buy to Open,1.0,0,2023-02-01,150,Call\n" \
                  "2023-01-02 10:00,AAPL,1,Sell to Close,1.2,0,2023-02-01,150,Call\n"
    res = analyze_csv(io.StringIO(csv_content))
    assert res is not None
    assert res["metrics"]["num_trades"] == 1
