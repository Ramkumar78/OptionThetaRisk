import pytest
import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _detect_broker
from option_auditor.parsers import TastytradeParser, TastytradeFillsParser
import option_auditor.main_analyzer as aud
import io
from datetime import datetime

def make_tasty_df(rows):
    return pd.DataFrame(rows)

def test_detect_broker():
    df = make_tasty_df([{"Underlying Symbol": "SPY"}])
    assert _detect_broker(df) == "tasty"

    df = make_tasty_df([{"Description": "FOO", "Symbol": "BAR"}])
    assert _detect_broker(df) == "tasty"

    df = make_tasty_df([{"Other": "Data"}])
    assert _detect_broker(df) is None

def test_basic_analysis():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 1.0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Call"}
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    res = analyze_csv(csv_buffer, broker="tasty")
    assert "error" not in res
    assert res["metrics"]["total_pnl"] == 48.0
    assert len(res["strategy_groups"]) == 1

def test_unsupported_broker():
    df = pd.DataFrame([{"Col1": 1, "Col2": 2}])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    res = analyze_csv(csv_buffer)
    assert "error" in res

def test_empty_csv():
    res = analyze_csv(io.StringIO(""))
    assert "error" in res

def test_no_options_trades():
    df = pd.DataFrame(columns=["Time", "Underlying Symbol", "Quantity", "Action", "Price", "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer)
    assert "error" in res

def test_verdict_logic():
    df1 = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df1.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res1 = analyze_csv(csv_buffer, style="income")
    assert res1['verdict'] == "Green Flag"

    df_amber = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-03 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        {"Time": "2025-01-04 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
        {"Time": "2025-01-06 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df_amber.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res_income = analyze_csv(csv_buffer, style="income")
    assert "Red Flag: Win Rate < 60%" in res_income['verdict']

    csv_buffer.seek(0)
    res_spec = analyze_csv(csv_buffer, style="speculation")
    assert "Amber: Low Win Rate" in res_spec['verdict']

    df2 = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df2.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res2 = analyze_csv(csv_buffer, style="income")
    assert "Red Flag: Negative Income" in res2['verdict']

def test_build_strategies_same_day_different_strategies():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Close", "Price": 1.1, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 400, "Option Type": "Call"},
        {"Time": "2025-01-01 14:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 405, "Option Type": "Call"},
        {"Time": "2025-01-01 14:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Close", "Price": 1.1, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 405, "Option Type": "Call"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer)
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

def test_buying_power_calculation():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0.0, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer, net_liquidity_now=10000, buying_power_available_now=2500)
    assert res["buying_power_utilized_percent"] == 75.0

    csv_buffer.seek(0)
    res_zero = analyze_csv(csv_buffer, net_liquidity_now=0, buying_power_available_now=0)
    assert res_zero["buying_power_utilized_percent"] is None

def test_rolling_trade_detection():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": "2025-01-10", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-01-05 10:01", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Sell to Open", "Price": 1.2, "Commissions and Fees": 0, "Expiration Date": "2025-02-20", "Strike Price": 400, "Option Type": "Put"},
        {"Time": "2025-02-10 10:00", "Underlying Symbol": "SPY", "Quantity": 1, "Action": "Buy to Close", "Price": 0.2, "Commissions and Fees": 0, "Expiration Date": "2025-02-20", "Strike Price": 400, "Option Type": "Put"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer)
    assert len(res["strategy_groups"]) == 1
    assert "Rolled" in res["strategy_groups"][0]["strategy"]
    assert res["strategy_groups"][0]["pnl"] == (100 - 50) + (120 - 20)

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

def test_no_closed_trades():
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0.10, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer)
    assert len(res["strategy_groups"]) == 1
    assert len(res["open_positions"]) == 1
