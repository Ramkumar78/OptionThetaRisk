import pandas as pd
import pytest
from option_auditor.main_analyzer import analyze_csv
import io

def make_tasty_df(rows):
    return pd.DataFrame(rows, columns=[
        "Time", "Underlying Symbol", "Quantity", "Action", "Price",
        "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"
    ])

def test_calendar_spread_grouping():
    rows = [
        {
            "Time": "2025-01-01 10:00:00",
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Action": "Sell to Open",
            "Price": 1.0,
            "Commissions and Fees": 0.0,
            "Expiration Date": "2025-01-17",
            "Strike Price": 400,
            "Option Type": "Call",
        },
        {
            "Time": "2025-01-01 10:00:05",
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Action": "Buy to Open",
            "Price": 1.5,
            "Commissions and Fees": 0.0,
            "Expiration Date": "2025-02-21",
            "Strike Price": 400,
            "Option Type": "Call",
        }
    ]

    df = make_tasty_df(rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    res = analyze_csv(csv_buffer, broker="tasty")

    strategies = res["strategy_groups"]
    assert len(strategies) == 1
    name = strategies[0]['strategy']
    assert "Calendar" in name or "Rolled" in name
