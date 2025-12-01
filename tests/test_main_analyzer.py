import pytest
import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _detect_broker
from option_auditor.parsers import TastytradeParser, TastytradeFillsParser
import option_auditor.main_analyzer as aud
import os
from datetime import datetime

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
    # Net PnL = 50 - 2 = 48.
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"}
    ])
    csv_path = write_csv(df, tmp_path / "test.csv")

    res = analyze_csv(str(csv_path), broker="tasty")
    assert "error" not in res
    assert res["metrics"]["total_pnl"] == 48.0 # Net PnL
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

def test_unsupported_broker(tmp_path):
    # Create CSV with unknown columns
    df = pd.DataFrame([{"Col1": 1, "Col2": 2}])
    csv_path = write_csv(df, tmp_path / "unknown.csv")

    # Auto detect should fail or return error
    res = analyze_csv(str(csv_path))
    assert "error" in res

def test_empty_csv(tmp_path):
    # Write an empty file
    with open(tmp_path / "empty.csv", "w") as f:
        pass
    res = analyze_csv(str(tmp_path / "empty.csv"))
    assert "error" in res

def test_no_options_trades(tmp_path):
    # CSV with structure but no data rows
    df = pd.DataFrame(columns=["Time", "Underlying Symbol", "Quantity", "Action", "Price", "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"])
    csv_path = write_csv(df, tmp_path / "headers_only.csv")
    res = analyze_csv(str(csv_path))
    assert "error" in res

def test_verdict_logic(tmp_path):
    # Green flag: Win rate > 50%, PnL > 0
    df1 = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ])
    csv_path1 = write_csv(df1, tmp_path / "green.csv")
    res1 = analyze_csv(str(csv_path1))
    assert res1['verdict'] == "Green flag"

    # Amber: Win rate < 50%, PnL > 0
    # Trade 1: Sell 1.0, Buy 0.5. +50.
    # Trade 2: Sell 0.6, Buy 0.7. -10.
    # Trade 3: Sell 0.6, Buy 0.7. -10.

    df_amber = make_tasty_df([
        # Win (+50)
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        # Loss (-10)
        {"Time": "2025-01-03 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        {"Time": "2025-01-04 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        # Loss (-10)
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
        {"Time": "2025-01-06 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
    ])
    csv_path_amber = write_csv(df_amber, tmp_path / "amber.csv")
    res_amber = analyze_csv(str(csv_path_amber))
    # Win rate: 1/3 = 33%. PnL: +30. Verdict: Amber.
    assert res_amber['verdict'] == "Amber"

    # Red flag: PnL < 0
    df2 = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ])
    csv_path2 = write_csv(df2, tmp_path / "red.csv")
    res2 = analyze_csv(str(csv_path2))
    assert res2['verdict'] == "Red flag"

def test_normalize_tasty_fills_fallback_parser_edge_cases(tmp_path):
    parser = TastytradeFillsParser()
    # Missing quantity
    df1 = pd.DataFrame([{"Time": "2025-01-01 10:00", "Description": "Jan 1 100 Call STO", "Price": "1.00 cr", "Symbol": "TEST", "Commissions": 0, "Fees": 0}])
    norm_df1 = parser.parse(df1)
    assert norm_df1.empty

    # Invalid quantity
    df2 = pd.DataFrame([{"Time": "2025-01-01 10:00", "Description": "X Jan 1 100 Call STO", "Price": "1.00 cr", "Symbol": "TEST", "Commissions": 0, "Fees": 0}])
    norm_df2 = parser.parse(df2)
    assert norm_df2.empty

    # Infer expiry year
    df3 = pd.DataFrame([{"Time": "2024-11-01 10:00", "Description": "1 Jan 1 100 Call STO", "Price": "1.00 cr", "Symbol": "TEST", "Commissions": 0, "Fees": 0}])
    norm_df3 = parser.parse(df3)
    assert norm_df3.iloc[0]["expiry"].year == 2025

def test_build_strategies_same_day_different_strategies(tmp_path):
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Close", "Price": 1.1, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-01 14:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 405, "Option Type": "Call"},
        {"Time": "2025-01-01 14:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Close", "Price": 1.1, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 405, "Option Type": "Call"},
    ])
    csv_path = write_csv(df, tmp_path / "multi_strat.csv")
    res = analyze_csv(str(csv_path))
    assert len(res["strategy_groups"]) == 2

def test_sym_desc_not_string():
    assert aud._sym_desc(123) == ""

def test_build_strategies_empty_df():
    from option_auditor.strategy import build_strategies
    df = pd.DataFrame(columns=["datetime", "contract_id", "symbol", "expiry", "strike", "right", "qty", "proceeds", "fees"])
    strategies = build_strategies(df)
    assert len(strategies) == 0

def test_sym_desc_unknown_symbol():
    assert aud._sym_desc("UNKNOWN") == "Options on UNKNOWN"

def test_analyze_csv_no_out_dir(tmp_path):
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0.0, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Sell to Close", "Price": 1.2, "Commissions and Fees": 0.0, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    csv_path = write_csv(df, tmp_path / "test.csv")
    res = analyze_csv(str(csv_path), out_dir=None)
    assert "trades.csv" not in os.listdir(tmp_path)

def test_normalize_tasty_zero_quantity():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 0, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0.0, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    parser = TastytradeParser()
    norm_df = parser.parse(df)
    assert norm_df.iloc[0]["qty"] == 0

def test_buying_power_calculation(tmp_path):
    csv_path = write_csv(make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0.0, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ]), tmp_path / "dummy.csv")
    res = analyze_csv(str(csv_path), net_liquidity_now=10000, buying_power_available_now=2500)
    assert res["buying_power_utilized_percent"] == 75.0

    # Test division by zero case
    res_zero = analyze_csv(str(csv_path), net_liquidity_now=0, buying_power_available_now=0)
    assert res_zero["buying_power_utilized_percent"] is None

def test_rolling_trade_detection(tmp_path):
    df = make_tasty_df([
        # Original position
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        # Roll: close original, open new
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-01-05 10:01", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.2, "Commissions and Fees": 0, "Expiration Date": "2025-02-20", "Strike Price": 400, "Option Type": "Put"},
        # Close rolled position
        {"Time": "2025-02-10 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.2, "Commissions and Fees": 0, "Expiration Date": "2025-02-20", "Strike Price": 400, "Option Type": "Put"},
    ])
    csv_path = write_csv(df, tmp_path / "roll.csv")
    res = analyze_csv(str(csv_path))
    assert len(res["strategy_groups"]) == 1
    assert "Rolled" in res["strategy_groups"][0]["strategy"]
    assert res["strategy_groups"][0]["pnl"] == (100 - 50) + (120 - 20)

def test_classify_strategy_three_legs():
    from option_auditor.strategy import _classify_strategy
    from option_auditor.models import StrategyGroup, TradeGroup, Leg
    strat = StrategyGroup(id="s1", symbol="TEST", expiry=pd.Timestamp("2025-01-01"))
    for i in range(3):
        leg = TradeGroup(contract_id=f"c{i}", symbol="TEST", expiry=pd.Timestamp("2025-01-01"), strike=100+i, right="C")
        leg.add_leg(Leg(ts=datetime.now(), qty=1, price=1, fees=0, proceeds=-100))
        strat.add_leg_group(leg)
    assert _classify_strategy(strat) == "Multi‑leg"

def test_invalid_strike_and_expiry():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": "invalid", "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Close", "Price": 2.00, "Commissions and Fees": 0, "Expiration Date": "invalid", "Strike Price": 10, "Option Type": "Call"},
    ])
    parser = TastytradeParser()
    norm_df = parser.parse(df)
    assert pd.isna(norm_df.iloc[0]["strike"])
    assert pd.isna(norm_df.iloc[1]["expiry"])

def test_group_contracts_with_open_empty_df():
    from option_auditor.main_analyzer import _group_contracts_with_open
    df = pd.DataFrame(columns=["datetime", "contract_id", "symbol", "expiry", "strike", "right", "qty", "proceeds", "fees"])
    closed, open = _group_contracts_with_open(df)
    assert len(closed) == 0
    assert len(open) == 0

def test_no_closed_trades(tmp_path):
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0.10, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    csv_path = write_csv(df, tmp_path / "open_only.csv")
    res = analyze_csv(str(csv_path))
    assert len(res["strategy_groups"]) == 1
    assert len(res["open_positions"]) == 1

def test_correlation_with_single_symbol(tmp_path):
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-01-01 12:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
    ])
    csv_path = write_csv(df, tmp_path / "single_symbol.csv")
    res = analyze_csv(str(csv_path))
    assert res.get("correlation_matrix") is None
