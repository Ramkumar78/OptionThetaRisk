import pytest
import pandas as pd
import numpy as np
import io
from option_auditor.parsers import (
    TastytradeParser, TastytradeFillsParser, IBKRParser, ManualInputParser
)
from datetime import datetime

# --- TastytradeParser Tests ---

def test_tasty_parser_date_parsing_edge_cases():
    parser = TastytradeParser()

    # Standard format: 2023-10-25 10:00
    ts = parser._parse_tasty_datetime("2023-10-25 10:00")
    assert ts == pd.Timestamp("2023-10-25 10:00")

    # Custom format: "Oct 25 10:00pm" (assumes current year)
    # If today is 2025-01-01, "Oct 25" is likely 2024.
    # The logic uses "now.year". If now is 2025, it tries 2025/10/25.
    # Then checks if dt > now + 2 days. 2025/10/25 > 2025/01/01? Yes.
    # So it subtracts a year -> 2024/10/25.

    # We can rely on relative behavior or mock datetime.now() if we want strict control.
    # But let's just check the fallback logic works at all.
    ts_custom = parser._parse_tasty_datetime("Oct 25 10:00pm")
    assert ts_custom is not None
    assert ts_custom.hour == 22 # 10pm -> 22:00

    # Invalid date
    ts_bad = parser._parse_tasty_datetime("NotADate")
    assert ts_bad is None

def test_tasty_parser_validation():
    parser = TastytradeParser()
    df_missing = pd.DataFrame({"Time": [], "Underlying Symbol": []}) # Missing Quantity etc.

    with pytest.raises(KeyError, match="Tasty CSV missing 'Quantity' column"):
        parser.parse(df_missing)

def test_tasty_parser_action_edge_cases():
    parser = TastytradeParser()
    df = pd.DataFrame({
        "Time": ["2023-10-25 10:00"],
        "Underlying Symbol": ["AAPL"],
        "Quantity": ["1"],
        "Action": ["Unknown Action"], # Should default to sign 1.0
        "Price": ["1.0"],
        "Commissions and Fees": ["0.0"],
        "Expiration Date": [None],
        "Strike Price": [None],
        "Option Type": [None]
    })

    out = parser.parse(df)
    assert out.iloc[0]["qty"] == 1.0 # default sign 1.0 * 1.0

# --- TastytradeFillsParser Tests ---

def test_tasty_fills_parser_fallback_logic():
    parser = TastytradeFillsParser()

    # Line that doesn't match main regex but has tokens
    # "100 AAPL @ 150.00" - simplistic manual-like entry in description?
    # The fallback logic looks for 6 tokens.
    # "100 Jan 20 150 Call" -> 5 tokens?
    # "100 Jan 20 23 150 Call" -> 6 tokens? (Qty, Mon, Day, Year?, Strike, Right)

    # Let's try to trigger the fallback parsing (lines 148+ in parsers.py)
    # It requires: Qty, Mon, Day, (optional 'd' or 'Exp'), Strike, Right
    # "10 Oct 25 150 Call" -> tokens: 10, Oct, 25, 150, Call
    # len=5. Fallback check "if len(toks) >= 6".
    # We need a 6th token or more. Maybe Year? Or extra garbage?
    # The code expects:
    # toks[0]: qty
    # toks[1]: mon
    # toks[2]: day
    # k starts at 3.
    # Optional: if toks[k] ends with 'd' or == 'exp', k+=1.
    # Then toks[k] = strike.
    # Then toks[k+1] = right.

    # So "10 Oct 25 2023 150 Call" ->
    # 0:10, 1:Oct, 2:25, 3:2023 (not d/exp), Strike=2023? No float conversion?
    # Wait, k=3. toks[3]="2023". float("2023") works.
    # toks[4]="150". Check right="150" -> not put/call. Continue.

    # Let's try "10 Oct 25 Exp 150 Call"
    # 0:10, 1:Oct, 2:25, 3:Exp (skip), 4:150 (Strike), 5:Call (Right).
    # This should work.

    df = pd.DataFrame([{
        "Description": "10 Oct 25 Exp 150 Call",
        "Price": "1.00",
        "Time": "2023-10-01 10:00",
        "Symbol": "AAPL",
        "Commissions": "0", "Fees": "0"
    }])

    res = parser.parse(df)
    assert len(res) == 1
    row = res.iloc[0]
    assert row["qty"] == 10.0
    assert row["strike"] == 150.0
    assert row["right"] == "C"

# --- IBKRParser Tests ---

def test_ibkr_parser_column_finding_failure():
    parser = IBKRParser()
    # Missing all
    df = pd.DataFrame({"Random": []})
    with pytest.raises(KeyError, match="IBKR Parser: Missing Symbol column"):
        parser.parse(df)

    # Missing Date
    df = pd.DataFrame({"Symbol": []})
    with pytest.raises(KeyError, match="IBKR Parser: Missing Date column"):
        parser.parse(df)

    # Missing Qty
    df = pd.DataFrame({"Symbol": [], "Date/Time": []})
    with pytest.raises(KeyError, match="IBKR Parser: Missing Quantity column"):
        parser.parse(df)

def test_ibkr_parser_explicit_asset_class():
    parser = IBKRParser()
    df = pd.DataFrame([{
        "Symbol": "AAPL",
        "Date/Time": "2023-10-25 10:00:00",
        "Quantity": "100",
        "Asset Class": "STK",
        "T. Price": "150.00"
    }])
    out = parser.parse(df)
    assert out.iloc[0]["asset_type"] == "STOCK"

# --- ManualInputParser Tests ---

def test_manual_parser_validation():
    parser = ManualInputParser()
    # Empty DF
    assert parser.parse(pd.DataFrame()).empty

    # Missing required 'date'
    df = pd.DataFrame({"symbol": ["AAPL"]})
    # It adds None cols for missing ones, but logic says:
    # "if col not in df.columns: ... df[col] = None"
    # Then proceeds.
    # datetime conversion: "None" -> NaT.
    # dropna(subset=["datetime"]) -> removes row.
    # Returns empty.

    out = parser.parse(df)
    assert out.empty

def test_manual_parser_stock_detection():
    parser = ManualInputParser()
    df = pd.DataFrame([{
        "date": "2023-10-25",
        "symbol": "AAPL",
        "action": "Buy",
        "qty": "100",
        "price": "150",
        "fees": "0",
        "expiry": "", # Empty expiry
        "strike": "", # Empty strike
        "right": ""   # Empty right
    }])

    out = parser.parse(df)
    assert len(out) == 1
    assert out.iloc[0]["asset_type"] == "STOCK"
    assert out.iloc[0]["contract_id"] == "AAPL:::0.0"

def test_manual_parser_opt_mapping():
    parser = ManualInputParser()
    df = pd.DataFrame([{
        "date": "2023-10-25",
        "symbol": "AAPL",
        "action": "Buy",
        "qty": "1",
        "price": "1.0",
        "fees": "0",
        "expiry": "2023-11-01",
        "strike": "150",
        "opt": "Call" # using 'opt' instead of 'right'
    }])

    out = parser.parse(df)
    assert len(out) == 1
    assert out.iloc[0]["right"] == "C"
    assert out.iloc[0]["asset_type"] == "OPT"
