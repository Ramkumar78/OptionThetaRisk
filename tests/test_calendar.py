import pandas as pd
import pytest
from option_auditor.main_analyzer import analyze_csv

def make_tasty_df(rows):
    return pd.DataFrame(rows, columns=[
        "Time", "Underlying Symbol", "Quantity", "Action", "Price",
        "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"
    ])

def write_csv(df: pd.DataFrame, path):
    df.to_csv(path, index=False)
    return path

def test_calendar_spread_grouping(tmp_path):
    # Scenario: Calendar Spread (Short Jan Call / Long Feb Call)
    # Executed almost simultaneously

    rows = [
        # Short Jan Call
        {
            "Time": "2025-01-01 10:00:00",
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Action": "Sell to Open",
            "Price": 1.0,
            "Commissions and Fees": 0.0,
            "Expiration Date": "2025-01-17", # Jan Expiry
            "Strike Price": 400,
            "Option Type": "Call",
        },
        # Long Feb Call
        {
            "Time": "2025-01-01 10:00:05", # 5 seconds later
            "Underlying Symbol": "SPY",
            "Quantity": 1,
            "Action": "Buy to Open",
            "Price": 1.5,
            "Commissions and Fees": 0.0,
            "Expiration Date": "2025-02-21", # Feb Expiry
            "Strike Price": 400,
            "Option Type": "Call",
        }
    ]

    df = make_tasty_df(rows)
    csv_path = write_csv(df, tmp_path / "calendar.csv")

    res = analyze_csv(str(csv_path), broker="tasty", out_dir=None)

    strategies = res["strategy_groups"]

    # We expect exactly 1 strategy
    assert len(strategies) == 1

    # Crucially, we expect the legs to be grouped within the strategy structure
    # If it was "Rolled", the legs wouldn't be merged into the list (based on current implementation analysis)
    # Let's verify via the 'strategy' object if we could access it, but here we have the dict output.
    # The dict output doesn't show leg count directly.
    # But we can check the strategy name. It should NOT be "Rolled..."
    print(f"Strategy Name: {strategies[0]['strategy']}")

    # Current broken behavior: "Rolled Short Call"
    # Expected fixed behavior: "Call Vertical (Debit)" or similar (until we add specific Calendar naming)
    # Definitely NOT "Rolled"
    assert "Rolled" not in strategies[0]["strategy"]
