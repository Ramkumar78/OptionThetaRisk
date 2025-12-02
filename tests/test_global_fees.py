import pytest
from option_auditor.main_analyzer import analyze_csv
import pandas as pd
import io

def test_analyze_with_global_fees():
    manual_data = [
        {"date": "2025-01-01", "symbol": "SPY", "action": "Sell Open", "qty": 1, "price": 1.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"},
        {"date": "2025-01-05", "symbol": "SPY", "action": "Buy Close", "qty": 1, "price": 0.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"}
    ]
    res1 = analyze_csv(manual_data=manual_data)
    assert res1["strategy_metrics"]["total_pnl"] == 100.0
    assert res1["strategy_metrics"]["total_fees"] == 0.0

    res2 = analyze_csv(manual_data=manual_data, global_fees=10.0)
    assert res2["strategy_metrics"]["total_gross_pnl"] == 100.0
    assert res2["strategy_metrics"]["total_fees"] == 20.0
    assert res2["strategy_metrics"]["total_pnl"] == 80.0

    assert res2["leakage_report"]["fee_drag"] == 20.0

def test_analyze_csv_global_fees_behavior():
    csv_content = """Time,Underlying Symbol,Action,Quantity,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type
2025-01-01 10:00,SPY,Sell to Open,1,1.00,1.00,2025-01-10,400,Put
2025-01-05 10:00,SPY,Buy to Close,1,0.00,1.00,2025-01-10,400,Put
"""
    res = analyze_csv(csv_path=io.StringIO(csv_content), global_fees=10.0)

    assert res["strategy_metrics"]["total_gross_pnl"] == 100.0
    assert res["strategy_metrics"]["total_fees"] == 22.0
    assert res["strategy_metrics"]["total_pnl"] == 78.0
