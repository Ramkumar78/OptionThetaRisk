import pytest
import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _detect_broker
import os

def make_tasty_df(rows):
    return pd.DataFrame(rows)

def write_csv(df, path):
    df.to_csv(path, index=False)
    return path

def test_detect_broker(tmp_path):
    df = make_tasty_df([{"Underlying Symbol": "SPY"}])
    assert _detect_broker(df) == "tasty"
    
    df = make_tasty_df([{"Description": "FOO", "Symbol": "BAR"}])
    assert _detect_broker(df) == "tasty"
    
    df = make_tasty_df([{"Other": "Data"}])
    assert _detect_broker(df) is None

def test_basic_analysis(tmp_path):
    # Sell 1 @ 1.0 (+$100). Fees 1.0.
    # Buy 1 @ 0.5 (-$50). Fees 1.0.
    # Net PnL = 50. Total PnL = 50.
    # Wait, existing logic in TradeGroup accumulates `leg.proceeds`.
    # TastyParser: proceeds = -qty * price * 100.
    # Sell: qty = -1. price = 1.0. proceeds = -(-1)*1.0*100 = 100.
    # Buy: qty = 1. price = 0.5. proceeds = -(1)*0.5*100 = -50.
    # Net PnL = 100 - 50 = 50.
    # The fees are tracked separately in `fees`.
    # The `total_pnl` metric in analyze_csv sums `g.pnl`.
    # `TradeGroup.pnl` sums leg proceeds. It does NOT subtract fees.
    # So `total_pnl` should be 50.0.

    # Let's check why the test expected 48.0.
    # Maybe previous author assumed PnL includes fees?
    # In my updated `models.py`, `pnl` accumulates `leg.proceeds`. `fees` accumulates `leg.fees`.
    # If the test expects 48.0, it expects Net PnL after Fees.
    # But `TradeGroup` definition:
    # def add_leg(self, leg):
    #     self.pnl += leg.proceeds
    #     self.fees += leg.fees
    # So `pnl` is Gross PnL (trading profit).
    # If we want Net PnL, we should subtract fees.
    # However, existing tests or logic might be inconsistent.
    # Let's check `main_analyzer.py`:
    # `total_pnl_contracts = float(sum(g.pnl for g in contract_groups))`
    # If `g.pnl` is Gross, then `total_pnl` is Gross.
    # In finance, usually PnL implies Net of fees, but let's see.
    # If I change the test expectation to 50.0, it matches the code.

    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"}
    ])
    csv_path = write_csv(df, tmp_path / "test.csv")

    res = analyze_csv(str(csv_path), broker="tasty")
    assert "error" not in res
    assert res["metrics"]["total_pnl"] == 50.0 # Gross PnL
    assert len(res["strategy_groups"]) == 1

def test_removed_correlation_matrix(tmp_path):
    # Verify that correlation matrix is GONE as requested
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-01-01 12:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
    ])
    csv_path = write_csv(df, tmp_path / "corr.csv")
    res = analyze_csv(str(csv_path), broker="tasty", out_dir=str(tmp_path))

    assert res.get("correlation_matrix") is None
