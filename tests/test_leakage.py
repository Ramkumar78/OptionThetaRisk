import pytest
from option_auditor.models import StrategyGroup
from option_auditor.main_analyzer import analyze_csv
import pandas as pd
from datetime import datetime
import io

def test_strategy_segments_tracking():
    s = StrategyGroup(id="s1", symbol="SPY", expiry=None)
    assert s.segments == []
    s.segments.append({"pnl": 100})
    assert len(s.segments) == 1
    assert s.segments[0]["pnl"] == 100

def test_leakage_metrics_calculation():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 12)

    data = [
        {
            "Time": start.isoformat(),
            "Action": "SELL_TO_OPEN",
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Price": 5.1,
            "Commissions and Fees": 1.0,
            "Expiration Date": "2023-02-17",
            "Strike Price": 400,
            "Option Type": "CALL"
        },
        {
            "Time": end.isoformat(),
            "Action": "BUY_TO_CLOSE",
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Price": 5.0,
            "Commissions and Fees": 1.0,
            "Expiration Date": "2023-02-17",
            "Strike Price": 400,
            "Option Type": "CALL"
        }
    ]

    df = pd.DataFrame(data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    result = analyze_csv(csv_buffer)

    if "error" in result:
        pytest.fail(f"Analysis failed with error: {result['error']}")

    assert "leakage_report" in result
    report = result["leakage_report"]

    assert report["fee_drag"] == 20.0
    assert "High Drag" in report["fee_drag_verdict"]

    stale = report["stale_capital"]
    assert len(stale) == 1
    assert stale[0]["symbol"] == "SPY"
    assert stale[0]["theta_per_day"] < 1.0
