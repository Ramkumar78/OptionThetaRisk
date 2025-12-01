import pytest
from option_auditor.main_analyzer import analyze_csv
import pandas as pd

def test_analyze_with_global_fees(tmp_path):
    # Setup simple manual data: 1 trade, PnL +100, Fees 0
    manual_data = [
        {"date": "2025-01-01", "symbol": "SPY", "action": "Sell Open", "qty": 1, "price": 1.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"},
        {"date": "2025-01-05", "symbol": "SPY", "action": "Buy Close", "qty": 1, "price": 0.0, "fees": 0.0, "expiry": "2025-01-10", "strike": 400, "right": "P"}
    ]
    # Gross PnL = 100 - 0 = 100.

    # Case 1: No global fees
    res1 = analyze_csv(manual_data=manual_data)
    assert res1["strategy_metrics"]["total_pnl"] == 100.0
    assert res1["strategy_metrics"]["total_fees"] == 0.0

    # Case 2: Global fees = 10.0
    res2 = analyze_csv(manual_data=manual_data, global_fees=10.0)
    assert res2["strategy_metrics"]["total_gross_pnl"] == 100.0
    assert res2["strategy_metrics"]["total_fees"] == 10.0
    assert res2["strategy_metrics"]["total_pnl"] == 90.0 # 100 - 10

    # Check Drag
    # Drag = 10 / 100 * 100 = 10%
    assert res2["leakage_report"]["fee_drag"] == 10.0
