import pytest
from option_auditor.main_analyzer import analyze_csv
import pandas as pd

def test_analyze_with_global_fees(tmp_path):
    # Setup simple manual data: 1 trade (Open + Close), PnL +100, Fees 0
    # Two rows: Open, Close
    manual_data = [
        {"date": "2025-01-01", "symbol": "SPY", "action": "Sell Open", "qty": 1, "price": 1.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"},
        {"date": "2025-01-05", "symbol": "SPY", "action": "Buy Close", "qty": 1, "price": 0.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"}
    ]
    # Gross PnL = 100 - 0 = 100.

    # Case 1: No global fees
    res1 = analyze_csv(manual_data=manual_data)
    assert res1["strategy_metrics"]["total_pnl"] == 100.0
    assert res1["strategy_metrics"]["total_fees"] == 0.0

    # Case 2: Global fees = 10.0 (Applied PER TRADE ROW)
    # 2 rows * 10.0 fee/row = 20.0 total fees
    res2 = analyze_csv(manual_data=manual_data, global_fees=10.0)
    assert res2["strategy_metrics"]["total_gross_pnl"] == 100.0
    assert res2["strategy_metrics"]["total_fees"] == 20.0
    assert res2["strategy_metrics"]["total_pnl"] == 80.0 # 100 - 20

    # Check Drag
    # Drag = 20 / 100 * 100 = 20%
    assert res2["leakage_report"]["fee_drag"] == 20.0

def test_analyze_csv_global_fees_behavior(tmp_path):
    # For CSV uploads, global_fees should still behave as a lump sum addition if provided (though UI hides it mostly)
    # We verify this to ensure we didn't break CSV logic.

    # Create dummy CSV
    # Note: We use positive values for fees here to match expectation of total_fees calculation
    csv_path = tmp_path / "test.csv"
    csv_content = """Time,Underlying Symbol,Action,Quantity,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type
2025-01-01 10:00,SPY,Sell to Open,1,1.00,1.00,2025-01-10,400,Put
2025-01-05 10:00,SPY,Buy to Close,1,0.00,1.00,2025-01-10,400,Put
"""
    csv_path.write_text(csv_content)

    # Gross PnL: Sell 1.0 (100), Buy 0.0 (0) => 100.
    # Fees in CSV: 1.0 + 1.0 = 2.0.

    # Run with global_fees = 10.0
    res = analyze_csv(csv_path=str(csv_path), global_fees=10.0)

    assert res["strategy_metrics"]["total_gross_pnl"] == 100.0
    # Total Fees = CSV Fees (2.0) + Global Lump Sum (10.0) = 12.0
    assert res["strategy_metrics"]["total_fees"] == 12.0
    assert res["strategy_metrics"]["total_pnl"] == 88.0
