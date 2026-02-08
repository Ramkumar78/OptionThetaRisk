import pytest
import pandas as pd
from datetime import datetime
from option_auditor.parsers import TastytradeFillsParser

@pytest.fixture
def parser():
    return TastytradeFillsParser()

def test_single_leg_option_fill_regex(parser):
    """Test 1: Single-leg option fills matching the regex."""
    df = pd.DataFrame([{
        "Description": "1 Jan 19 150 Call BTO",
        "Price": "5.00",
        "Time": "2024-01-01 10:00",
        "Symbol": "AAPL",
        "Commissions": "1.0",
        "Fees": "0.1"
    }])
    result = parser.parse(df)

    assert len(result) == 1
    row = result.iloc[0]
    assert row['symbol'] == "AAPL"
    assert row['strike'] == 150.0
    assert row['right'] == "C"
    assert row['qty'] == 1.0
    # Proceeds: -1 * 5.00 * 100 = -500.0 (Debit)
    assert row['proceeds'] == -500.0
    # Fees: 1.0 + 0.1 = 1.1
    assert row['fees'] == 1.1

def test_single_leg_option_fill_credit(parser):
    """Test single leg credit fill."""
    df = pd.DataFrame([{
        "Description": "-1 Jan 19 150 Put STO",
        "Price": "2.00 cr",
        "Time": "2024-01-01 10:00",
        "Symbol": "AAPL",
        "Commissions": "1.0",
        "Fees": "0.1"
    }])
    result = parser.parse(df)

    assert len(result) == 1
    row = result.iloc[0]
    assert row['qty'] == -1.0
    # Credit means positive money
    # 2.00 * 100 = 200.0
    assert row['proceeds'] == 200.0

def test_multiline_complex_spread(parser):
    """Test 2: Multi-line descriptions for complex spreads."""
    # Vertical Spread
    desc = "-1 Jan 19 150 Put STO\n1 Jan 19 145 Put BTO"
    df = pd.DataFrame([{
        "Description": desc,
        "Price": "1.50 cr",
        "Time": "2024-01-01 10:00",
        "Symbol": "XYZ",
        "Commissions": "2.0",
        "Fees": "0.2"
    }])
    result = parser.parse(df)
    assert len(result) == 2

    # Sort by strike to distinguish
    result = result.sort_values("strike")

    # Leg 145 Put (Long)
    leg1 = result.iloc[0]
    assert leg1['strike'] == 145.0
    assert leg1['qty'] == 1.0
    assert leg1['right'] == 'P'

    # Leg 150 Put (Short)
    leg2 = result.iloc[1]
    assert leg2['strike'] == 150.0
    assert leg2['qty'] == -1.0
    assert leg2['right'] == 'P'

def test_ratio_logic_distribution(parser):
    """Test 3: Ensure the ratio logic correctly distributes proceeds and fees across multiple legs based on quantity."""
    # 2 legs: one with qty 2, one with qty 1. Total qty = 3.
    # Price $3.00 (debit). Total money = -3.00 * 100 = -300.
    # Fees $3.00.

    desc = "2 Jan 19 100 Call BTO\n1 Jan 19 110 Call BTO"
    df = pd.DataFrame([{
        "Description": desc,
        "Price": "3.00",
        "Time": "2024-01-01 10:00",
        "Symbol": "ABC",
        "Commissions": "3.0",
        "Fees": "0.0"
    }])
    result = parser.parse(df)
    assert len(result) == 2

    leg_qty_2 = result[result['qty'] == 2.0].iloc[0]
    leg_qty_1 = result[result['qty'] == 1.0].iloc[0]

    # Ratio:
    # Total legs qty = 3
    # Leg 2 qty ratio: 2/3. Proceeds: -300 * (2/3) = -200.
    # Leg 1 qty ratio: 1/3. Proceeds: -300 * (1/3) = -100.

    assert pytest.approx(leg_qty_2['proceeds']) == -200.0
    assert pytest.approx(leg_qty_1['proceeds']) == -100.0

    # Fees distribution matches ratio
    # Total fees 3.0.
    # Leg 2 fees: 3.0 * (2/3) = 2.0
    # Leg 1 fees: 3.0 * (1/3) = 1.0
    assert pytest.approx(leg_qty_2['fees']) == 2.0
    assert pytest.approx(leg_qty_1['fees']) == 1.0

def test_year_adjustment_logic_next_year(parser):
    """Test 4: Year-adjustment logic for expirations that cross into the next calendar year."""
    # Trade in Nov 2023, Expiry in Jan (implies 2024)
    # Logic: if ts.month > 10 and month_num < 3: expiry_year += 1
    df = pd.DataFrame([{
        "Description": "1 Jan 19 150 Call BTO",
        "Price": "1.00",
        "Time": "2023-11-15 10:00",
        "Symbol": "FWD",
        "Commissions": "0",
        "Fees": "0"
    }])
    result = parser.parse(df)
    row = result.iloc[0]

    # Trade year is 2023.
    # Expiry month Jan (1).
    # 2023 + 1 = 2024.
    assert row['expiry'].year == 2024
    assert row['expiry'].month == 1
    assert row['expiry'].day == 19

def test_year_adjustment_logic_same_year(parser):
    """Test 4b: Year-adjustment logic for same year (e.g. Trade Jan, Exp Feb)."""
    df = pd.DataFrame([{
        "Description": "1 Feb 15 150 Call BTO",
        "Price": "1.00",
        "Time": "2023-01-15 10:00",
        "Symbol": "FWD",
        "Commissions": "0",
        "Fees": "0"
    }])
    result = parser.parse(df)
    row = result.iloc[0]

    assert row['expiry'].year == 2023
    assert row['expiry'].month == 2
    assert row['expiry'].day == 15

def test_desc_regex_variations(parser):
    """Test regex variations including 'Exp', 'dte'."""
    data = [
        ("1 Feb 15 Exp 100 Call BTO", 2, 15), # With Exp
        ("-1 Mar 1 10d 100 Put STO", 3, 1),   # With 10d
        ("1 Apr 20 100 Call BTO", 4, 20),     # Without dte/Exp
    ]

    rows = []
    for i, (desc, m, d) in enumerate(data):
        rows.append({
            "Description": desc,
            "Price": "1.00",
            "Time": "2024-01-01 10:00",
            "Symbol": f"S{i}",
            "Commissions": "0", "Fees": "0"
        })

    df = pd.DataFrame(rows)
    result = parser.parse(df)

    assert len(result) == 3

    # Verify parsing
    row0 = result[result['symbol'] == "S0"].iloc[0]
    assert row0['expiry'].month == 2
    assert row0['expiry'].day == 15

    row1 = result[result['symbol'] == "S1"].iloc[0]
    assert row1['expiry'].month == 3
    assert row1['expiry'].day == 1

    row2 = result[result['symbol'] == "S2"].iloc[0]
    assert row2['expiry'].month == 4
    assert row2['expiry'].day == 20
