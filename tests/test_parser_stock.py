
import pytest
import pandas as pd
from option_auditor.parsers import IBKRParser, TastytradeParser

def test_ibkr_parser_stock():
    # Test that IBKR Parser now handles stock trades
    data = [
        # Symbol, DateTime, Quantity, Price, Proceeds, Comm/Fee, AssetClass, Right
        {"Symbol": "AAPL", "DateTime": "20231025;100000", "Quantity": "100", "T. Price": "150.00", "Proceeds": "-15000", "Comm/Fee": "-1.0", "AssetClass": "STK", "Put/Call": ""},
        {"Symbol": "AAPL", "DateTime": "20231025;100500", "Quantity": "-1", "T. Price": "1.00", "Proceeds": "100", "Comm/Fee": "-1.0", "AssetClass": "OPT", "Put/Call": "C", "Strike": "155", "Expiry": "20231027"}
    ]
    df = pd.DataFrame(data)
    parser = IBKRParser()
    out = parser.parse(df)

    assert len(out) == 2

    stock = out[out["asset_type"] == "STOCK"].iloc[0]
    assert stock["symbol"] == "AAPL"
    assert stock["qty"] == 100
    assert stock["proceeds"] == -15000
    assert stock["contract_id"] == "AAPL:::0.0"

    opt = out[out["asset_type"] == "OPT"].iloc[0]
    assert opt["symbol"] == "AAPL"
    assert opt["qty"] == -1
    assert opt["proceeds"] == 100

def test_ibkr_parser_stock_implicit():
    # Test implicit stock detection (empty right)
    data = [
        {"Symbol": "AAPL", "DateTime": "20231025;100000", "Quantity": "100", "T. Price": "150.00", "Proceeds": "-15000", "Comm/Fee": "-1.0", "Put/Call": ""},
    ]
    df = pd.DataFrame(data)
    parser = IBKRParser()
    out = parser.parse(df)

    assert len(out) == 1
    stock = out.iloc[0]
    assert stock["asset_type"] == "STOCK"
    assert stock["contract_id"] == "AAPL:::0.0"

def test_tasty_parser_stock():
    # Test Tastytrade parser handles stock
    data = {
        "Time": ["2023-10-25 10:00", "2023-10-25 10:05"],
        "Underlying Symbol": ["AAPL", "AAPL"],
        "Quantity": ["100", "1"],
        "Action": ["Buy", "Sell to Open"],
        "Price": ["150.00", "1.00"],
        "Commissions and Fees": ["0.00", "1.10"],
        "Expiration Date": [None, "10/27/2023"],
        "Strike Price": [None, "155.0"],
        "Option Type": [None, "Call"]
    }
    df = pd.DataFrame(data)
    parser = TastytradeParser()
    out = parser.parse(df)

    assert len(out) == 2
    stock = out[out["asset_type"] == "STOCK"].iloc[0]
    assert stock["symbol"] == "AAPL"
    assert stock["qty"] == 100.0 # Buy = +1 * 100? No, Buy=1.0. Qty raw=100.
    # TastyParser: sign=1.0 for Buy. qty=100 * 1.0 = 100.
    assert stock["qty"] == 100.0
    # Proceeds: -qty * price * multiplier(1). -100 * 150 * 1 = -15000.
    assert stock["proceeds"] == -15000.0

    opt = out[out["asset_type"] == "OPT"].iloc[0]
    assert opt["qty"] == -1.0 # Sell to Open
    assert opt["proceeds"] == -(-1.0) * 1.00 * 100.0 # 100.0
