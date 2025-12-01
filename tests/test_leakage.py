import pytest
from option_auditor.models import StrategyGroup, TradeGroup, Leg
from option_auditor.main_analyzer import analyze_csv
import pandas as pd
from datetime import datetime, timedelta

def test_strategy_segments_tracking():
    # Verify StrategyGroup model update
    s = StrategyGroup(id="s1", symbol="SPY", expiry=None)
    assert s.segments == []

    # Verify we can append dicts
    s.segments.append({"pnl": 100})
    assert len(s.segments) == 1
    assert s.segments[0]["pnl"] == 100

def test_leakage_metrics_calculation(tmp_path):
    # We create a CSV that matches the REQUIRED columns of TastytradeParser
    # "Time", "Underlying Symbol", "Quantity", "Action", "Price", "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"

    csv_path = tmp_path / "test_trades.csv"

    # Dates
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 12) # 11 days later

    # 1. Open Trade (Sell to Open Call) -> Credit
    # 2. Close Trade (Buy to Close Call) -> Debit
    # Net PnL = Credit - Debit.
    # Example: Sell for 5.0 (Credit $500). Buy back for 5.1 (Debit $510). PnL = -$10.
    # Fees = $1 each leg. Total Fees = $2.
    # This example gives Negative PnL.

    # Let's create a Profitable trade to test Fee Drag correctly (Drag on Profit).
    # Sell for 5.1 ($510). Buy back for 5.0 ($500). PnL = +$10.
    # Fees = $1 each leg. Total Fees = $2.
    # Gross Profit = Net PnL ($10) + Fees ($2) = $12.
    # Drag = 2 / 12 = 16.6% > 10%. VERDICT: High Drag.

    # "Stale Capital": Held > 10d. PnL $10 / 11 days < $1/day.

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
    df.to_csv(csv_path, index=False)

    # Run analysis
    result = analyze_csv(str(csv_path))

    if "error" in result:
        pytest.fail(f"Analysis failed with error: {result['error']}")

    assert "leakage_report" in result
    report = result["leakage_report"]

    # Check Fee Drag
    # Net PnL = (5.1 - 5.0)*100 = 10.
    # Fees = 2.
    # Gross PnL = 12.
    # Drag = 2/12 = 16.67%
    assert 16.6 < report["fee_drag"] < 16.7
    assert "High Drag" in report["fee_drag_verdict"]

    # Check Stale Capital
    # Hold days ~ 11. PnL 10. Theta 0.9.
    stale = report["stale_capital"]
    assert len(stale) == 1
    assert stale[0]["symbol"] == "SPY"
    # assert stale[0]["theta_per_day"] < 1.0 # Might be close due to float math
    # 10 / 11 = 0.909...
    assert stale[0]["theta_per_day"] < 1.0
