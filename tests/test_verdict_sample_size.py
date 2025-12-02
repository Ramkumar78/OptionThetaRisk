import pytest
import pandas as pd
import io
import os
from unittest.mock import patch
from option_auditor.main_analyzer import analyze_csv

def make_tasty_df(rows):
    return pd.DataFrame(rows)

def test_verdict_sample_size_gating():
    # Only 2 trades, profitable
    df = make_tasty_df([
        # Trade 1: Profitable
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 2.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        # Trade 2: Profitable
        {"Time": "2025-01-06 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 2.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-15", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-10 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-15", "Strike Price": 400, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    res = analyze_csv(csv_buffer, style="income")

    # Normally this would be "Green Flag", but we expect "Insufficient Data"
    assert "Insufficient Data" in res["verdict"]
    assert res["verdict_color"] == "gray"

    # Now verify with > 10 trades
    rows = []
    for i in range(11):
        rows.append({"Time": f"2025-01-{i+1:02d} 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 2.0, "Commissions and Fees": 1.0, "Expiration Date": f"2025-02-{i+1:02d}", "Strike Price": 400, "Option Type": "Call"})
        rows.append({"Time": f"2025-01-{i+1:02d} 14:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": f"2025-02-{i+1:02d}", "Strike Price": 400, "Option Type": "Call"})

    df_11 = make_tasty_df(rows)
    csv_buffer = io.StringIO()
    df_11.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    res_11 = analyze_csv(csv_buffer, style="income")
    assert res_11["verdict"] == "Green Flag"
    assert res_11["verdict_color"] == "green"

def test_verdict_configurable_sample_size():
    # Test that we can change the threshold via env var
    # Note: option_auditor.config is imported at module level in main_analyzer.
    # To test this properly, we'd need to reload the module or patch the imported variable.
    # Since patching imports can be tricky with pytest, patching option_auditor.main_analyzer.VERDICT_MIN_TRADES is easier.

    # Use 2 trades (default threshold 10 would hide verdict)
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 2.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-06 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 2.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-15", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-10 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-15", "Strike Price": 400, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    # Patch the variable in main_analyzer
    with patch("option_auditor.main_analyzer.VERDICT_MIN_TRADES", 1):
        res = analyze_csv(csv_buffer, style="income")
        assert res["verdict"] == "Green Flag"
        assert res["verdict_color"] == "green"

    # Verify fallback to default behavior (should be insufficient data)
    # We need to reload or ensure the patch is reverted. 'with patch' handles reversion.
    # However, since the variable was imported, the module-level variable in main_analyzer is what we patched.
    # So outside the block it should be back to 10.

    csv_buffer.seek(0)
    res_default = analyze_csv(csv_buffer, style="income")
    assert "Insufficient Data" in res_default["verdict"]
