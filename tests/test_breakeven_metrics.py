import pytest
import pandas as pd
from datetime import datetime, timedelta
from option_auditor.main_analyzer import analyze_csv

def test_open_position_breakeven_metrics():
    """
    Test calculation of Average Entry Price and Breakeven for open positions.
    """

    # Define a future expiry date to ensure positions remain open
    expiry_date = (datetime.now() + timedelta(days=30)).date().isoformat()

    # Manual data simulating user input
    # 1. Short Put (Credit Strategy)
    #    Action: Sell to Open
    #    Qty: 1 (User input, parser converts to -1)
    #    Price: $1.50 (Credit per share)
    #    Strike: 100
    #    Expected Avg Price: $1.50
    #    Expected Breakeven: Strike - Credit = 100 - 1.50 = 98.50

    # 2. Long Call (Debit Strategy)
    #    Action: Buy to Open
    #    Qty: 1 (User input, parser converts to +1)
    #    Price: $2.00 (Debit per share)
    #    Strike: 105
    #    Expected Avg Price: $2.00
    #    Expected Breakeven: Strike + Debit = 105 + 2.00 = 107.00

    # 3. Short Call (Credit Strategy)
    #    Action: Sell to Open
    #    Qty: 1
    #    Price: $3.00
    #    Strike: 110
    #    Expected Avg Price: $3.00
    #    Expected Breakeven: Strike + Credit = 110 + 3.00 = 113.00

    # 4. Long Put (Debit Strategy)
    #    Action: Buy to Open
    #    Qty: 1
    #    Price: $4.00
    #    Strike: 90
    #    Expected Avg Price: $4.00
    #    Expected Breakeven: Strike - Debit = 90 - 4.00 = 86.00

    manual_data = [
        # Case 1: Short Put
        {
            "date": (datetime.now() - timedelta(days=5)).isoformat(),
            "symbol": "SPUT",
            "action": "Sell to Open",
            "qty": 1,
            "price": 1.50,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 100.0,
            "right": "P"
        },
        # Case 2: Long Call
        {
            "date": (datetime.now() - timedelta(days=5)).isoformat(),
            "symbol": "LCALL",
            "action": "Buy to Open",
            "qty": 1,
            "price": 2.00,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 105.0,
            "right": "C"
        },
        # Case 3: Short Call
        {
            "date": (datetime.now() - timedelta(days=5)).isoformat(),
            "symbol": "SCALL",
            "action": "Sell to Open",
            "qty": 1,
            "price": 3.00,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 110.0,
            "right": "C"
        },
        # Case 4: Long Put
        {
            "date": (datetime.now() - timedelta(days=5)).isoformat(),
            "symbol": "LPUT",
            "action": "Buy to Open",
            "qty": 1,
            "price": 4.00,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 90.0,
            "right": "P"
        }
    ]

    result = analyze_csv(manual_data=manual_data, broker="manual")

    open_positions = result.get("open_positions", [])
    assert len(open_positions) == 4, f"Expected 4 open positions, found {len(open_positions)}"

    # Helper to find by symbol
    def get_pos(sym):
        return next((p for p in open_positions if p['symbol'] == sym), None)

    # Verify Short Put
    sput = get_pos("SPUT")
    assert sput is not None
    assert sput['avg_price'] == pytest.approx(1.50)
    assert sput['breakeven'] == pytest.approx(98.50)

    # Verify Long Call
    lcall = get_pos("LCALL")
    assert lcall is not None
    assert lcall['avg_price'] == pytest.approx(2.00)
    assert lcall['breakeven'] == pytest.approx(107.00)

    # Verify Short Call
    scall = get_pos("SCALL")
    assert scall is not None
    assert scall['avg_price'] == pytest.approx(3.00)
    assert scall['breakeven'] == pytest.approx(113.00)

    # Verify Long Put
    lput = get_pos("LPUT")
    assert lput is not None
    assert lput['avg_price'] == pytest.approx(4.00)
    assert lput['breakeven'] == pytest.approx(86.00)

def test_averaged_entry_price():
    """
    Test that average price is calculated correctly when multiple entries exist.
    """
    expiry_date = (datetime.now() + timedelta(days=30)).date().isoformat()

    # Scenario:
    # 1. Sell 1 Put @ $1.00
    # 2. Sell 1 Put @ $2.00
    # Total Qty: 2 (Short)
    # Total Proceeds: 100 + 200 = 300
    # Avg Price: 300 / (2 * 100) = 1.50
    # Breakeven: Strike - 1.50

    manual_data = [
        {
            "date": (datetime.now() - timedelta(days=5)).isoformat(),
            "symbol": "AVG",
            "action": "Sell to Open",
            "qty": 1,
            "price": 1.00,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 50.0,
            "right": "P"
        },
        {
            "date": (datetime.now() - timedelta(days=4)).isoformat(),
            "symbol": "AVG",
            "action": "Sell to Open",
            "qty": 1,
            "price": 2.00,
            "fees": 1.0,
            "expiry": expiry_date,
            "strike": 50.0,
            "right": "P"
        }
    ]

    result = analyze_csv(manual_data=manual_data, broker="manual")
    open_positions = result.get("open_positions", [])

    avg_pos = next((p for p in open_positions if p['symbol'] == "AVG"), None)
    assert avg_pos is not None
    assert avg_pos['qty_open'] == -2.0
    assert avg_pos['avg_price'] == pytest.approx(1.50)
    assert avg_pos['breakeven'] == pytest.approx(48.50) # 50 - 1.50
