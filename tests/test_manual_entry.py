import pytest
import pandas as pd
from option_auditor.parsers import ManualInputParser
from option_auditor.main_analyzer import analyze_csv

def test_manual_input_parser():
    parser = ManualInputParser()

    data = [
        {"date": "2025-01-01", "symbol": "SPY", "action": "Sell Open", "qty": 1, "price": 1.0, "fees": 1.0, "expiry": "2025-01-10", "strike": 400, "right": "P"},
        {"date": "2025-01-05", "symbol": "SPY", "action": "Buy Close", "qty": 1, "price": 0.5, "fees": 1.0, "expiry": "2025-01-10", "strike": 400, "right": "P"}
    ]
    df = pd.DataFrame(data)
    norm_df = parser.parse(df)

    assert len(norm_df) == 2
    assert norm_df.iloc[0]["qty"] == -1.0
    assert norm_df.iloc[0]["proceeds"] == 100.0
    assert norm_df.iloc[0]["fees"] == 1.0

    assert norm_df.iloc[1]["qty"] == 1.0
    assert norm_df.iloc[1]["proceeds"] == -50.0
    assert norm_df.iloc[1]["fees"] == 1.0

def test_manual_parser_edge_cases():
    parser = ManualInputParser()

    df = pd.DataFrame()
    assert parser.parse(df).empty

    df_missing = pd.DataFrame([{"date": "2025-01-01", "symbol": "SPY"}])
    norm = parser.parse(df_missing)
    assert not norm.empty
    assert len(norm) == 1
    assert norm.iloc[0]["symbol"] == "SPY"

def test_analyze_with_manual_data():
    manual_data = [
        {"date": "2025-01-01", "symbol": "SPY", "action": "Sell Open", "qty": 1, "price": 1.0, "fees": 1.0, "expiry": "2025-01-10", "strike": 400, "right": "P"},
        {"date": "2025-01-05", "symbol": "SPY", "action": "Buy Close", "qty": 1, "price": 0.5, "fees": 1.0, "expiry": "2025-01-10", "strike": 400, "right": "P"}
    ]

    res = analyze_csv(manual_data=manual_data)

    assert "error" not in res
    assert len(res["strategy_groups"]) == 1
    assert res["metrics"]["total_pnl"] == 48.0
    assert res["metrics"]["total_fees"] == 2.0
    assert res["strategy_metrics"]["total_gross_pnl"] == 50.0
    assert res["leakage_report"]["fee_drag"] == 4.0
