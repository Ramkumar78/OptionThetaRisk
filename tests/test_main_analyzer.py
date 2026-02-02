import pytest
import pandas as pd
from option_auditor.main_analyzer import analyze_csv, _detect_broker
from option_auditor.parsers import TastytradeParser, TastytradeFillsParser
import option_auditor.main_analyzer as aud
import io
from datetime import datetime
from unittest.mock import patch, MagicMock

def make_tasty_df(rows):
    return pd.DataFrame(rows)

def test_detect_broker():
    df = make_tasty_df([{"Underlying Symbol": "SPY"}])
    assert _detect_broker(df) == "tasty"

    df = make_tasty_df([{"Description": "FOO", "Symbol": "BAR"}])
    assert _detect_broker(df) == "tasty"

    df = make_tasty_df([{"Other": "Data"}])
    assert _detect_broker(df) is None

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_basic_analysis(mock_fetch):
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

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_verdict_logic(mock_fetch):
    # Case 1: Green Flag (need 10+ trades, all wins or mostly wins)
    rows1 = [
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ]
    # Add 9 profitable trades
    for i in range(9):
        rows1.append({"Time": f"2025-03-{i+1:02d} 10:00", "Underlying Symbol": "PAD", "Quantity": 1, "Action": "Sell to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 10, "Option Type": "Call"})
        rows1.append({"Time": f"2025-03-{i+1:02d} 14:00", "Underlying Symbol": "PAD", "Quantity": 1, "Action": "Buy to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 10, "Option Type": "Call"})

    df1 = make_tasty_df(rows1)
    csv_buffer = io.StringIO()
    df1.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res1 = analyze_csv(csv_buffer, style="income")
    assert res1['verdict'] == "Green Flag"

    # Case 2: Amber/Red Flag (Low Win Rate)
    # Original: 1 win, 2 losses.
    # Win rate 33%. PnL 0.3.
    rows_amber = [
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-03 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        {"Time": "2025-01-04 10:00", "Underlying Symbol": "B", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 20, "Option Type": "Call"},
        {"Time": "2025-01-05 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Sell to Open", "Price": 0.60, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
        {"Time": "2025-01-06 10:00", "Underlying Symbol": "C", "Quantity": 1, "Action": "Buy to Close", "Price": 0.70, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 30, "Option Type": "Call"},
    ]
    # Add 7 losing trades but keep total PnL positive.
    # Current PnL = 0.3.
    # If I add 1 large win: +10.0.
    # And 6 losses: -0.1 each = -0.6.
    # Total PnL = 0.3 + 10.0 - 0.6 = 9.7 (Positive).
    # Total Trades: 3 + 1 + 6 = 10.
    # Total Wins: 1 + 1 = 2.
    # Total Losses: 2 + 6 = 8.
    # Win Rate: 2/10 = 20%. (< 35% and < 60%).

    # Large Win
    rows_amber.append({"Time": "2025-02-01 10:00", "Underlying Symbol": "WIN", "Quantity": 1, "Action": "Sell to Open", "Price": 11.0, "Commissions and Fees": 0, "Expiration Date": "2025-03-01", "Strike Price": 100, "Option Type": "Call"})
    rows_amber.append({"Time": "2025-02-01 14:00", "Underlying Symbol": "WIN", "Quantity": 1, "Action": "Buy to Close", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": "2025-03-01", "Strike Price": 100, "Option Type": "Call"})

    # 6 Small Losses
    for i in range(6):
        rows_amber.append({"Time": f"2025-03-{i+1:02d} 10:00", "Underlying Symbol": "LOSS", "Quantity": 1, "Action": "Sell to Open", "Price": 0.6, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 20, "Option Type": "Call"})
        rows_amber.append({"Time": f"2025-03-{i+1:02d} 14:00", "Underlying Symbol": "LOSS", "Quantity": 1, "Action": "Buy to Close", "Price": 0.7, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 20, "Option Type": "Call"})

    df_amber = make_tasty_df(rows_amber)
    csv_buffer = io.StringIO()
    df_amber.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res_income = analyze_csv(csv_buffer, style="income")
    assert "Red Flag: Win Rate < 60%" in res_income['verdict']

    csv_buffer.seek(0)
    res_spec = analyze_csv(csv_buffer, style="speculation")
    assert "Amber: Low Win Rate" in res_spec['verdict']

    # Case 3: Negative Income
    rows2 = [
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
        {"Time": "2025-01-02 10:00", "Underlying Symbol": "A", "Quantity": 1, "Action": "Sell to Close", "Price": 0.50, "Commissions and Fees": 0, "Expiration Date": "2025-02-21", "Strike Price": 10, "Option Type": "Call"},
    ]
    # Add 9 losing trades
    for i in range(9):
        rows2.append({"Time": f"2025-03-{i+1:02d} 10:00", "Underlying Symbol": "LOSS", "Quantity": 1, "Action": "Buy to Open", "Price": 1.0, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 10, "Option Type": "Call"})
        rows2.append({"Time": f"2025-03-{i+1:02d} 14:00", "Underlying Symbol": "LOSS", "Quantity": 1, "Action": "Sell to Close", "Price": 0.5, "Commissions and Fees": 0, "Expiration Date": f"2025-04-{i+1:02d}", "Strike Price": 10, "Option Type": "Call"})

    df2 = make_tasty_df(rows2)
    csv_buffer = io.StringIO()
    df2.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res2 = analyze_csv(csv_buffer, style="income")
    assert "Red Flag: Negative Income" in res2['verdict']

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_build_strategies_same_day_different_strategies(mock_fetch):
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

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_buying_power_calculation(mock_fetch):
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

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_rolling_trade_detection(mock_fetch):
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

@patch('option_auditor.main_analyzer._fetch_live_prices', return_value={})
def test_no_closed_trades(mock_fetch):
    df = make_tasty_df([
        {"Time": "2025-01-01 10:00", "Underlying Symbol": "MSFT", "Quantity": 1, "Action": "Buy to Open", "Price": 1.00, "Commissions and Fees": 0.10, "Expiration Date": "2025-02-21", "Strike Price": 500, "Option Type": "Put"},
    ])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    res = analyze_csv(csv_buffer)
    assert len(res["strategy_groups"]) == 1
    assert len(res["open_positions"]) == 1

# --- Migrated from test_main_analyzer_coverage.py ---

@patch('option_auditor.main_analyzer._fetch_live_prices')
def test_refresh_dashboard_data_redefined(mock_fetch_prices):
    saved_data = {
        "summary": {"total_pnl": 100},
        "open_positions": [
            {
                "symbol": "AAPL",
                "contract_id": "AAPL:2025-01-01:C:150",
                "contract": "C 150.0",
                "qty_open": 1,
                "avg_price": 5.0,
                "current_price": 0.0,
                "expiry": "2025-01-01",
                "strike": 150,
                "right": "C"
            }
        ],
        "verdict": {"color": "gray"}
    }

    mock_fetch_prices.return_value = {"AAPL": 155.0}

    updated = aud.refresh_dashboard_data(saved_data)

    pos = updated["open_positions"][0]
    assert pos["current_price"] == 155.0


@patch('option_auditor.main_analyzer._fetch_live_prices')
def test_refresh_dashboard_data_risk(mock_fetch_prices):
    saved_data = {
        "summary": {"total_pnl": 100},
        "open_positions": [
            {
                "symbol": "AAPL",
                "contract_id": "AAPL:2025-01-01:C:140",
                "contract": "C 140.0",
                "qty_open": -5,         # Short 5 Calls
                "avg_price": 5.0,
                "current_price": 0.0,
                "expiry": "2025-01-01",
                "strike": 140.0,
                "right": "C"
            }
        ],
        "verdict": {"color": "gray"}
    }

    mock_fetch_prices.return_value = {"AAPL": 150.0}

    updated = aud.refresh_dashboard_data(saved_data)

    pos = updated["open_positions"][0]
    assert "risk_alert" in pos
    assert pos["risk_alert"] == "ITM Risk"

    assert "High Open Risk" in updated["verdict"]

@patch('option_auditor.main_analyzer.TastytradeFillsParser')
@patch('option_auditor.main_analyzer.build_strategies')
def test_analyze_csv_empty(mock_build, mock_parser_cls):
    # If parse returns empty
    mock_parser = MagicMock()
    mock_parser_cls.return_value = mock_parser
    mock_parser.parse.return_value = pd.DataFrame()

    res = analyze_csv(None, "auto")
    assert "error" in res
    assert res["error"] == "No input data provided"

@patch('option_auditor.main_analyzer.build_strategies')
def test_analyze_csv_manual(mock_build):
    manual_data = [{
        "symbol": "AAPL",
        "date": "2023-01-01",
        "time": "10:00:00",
        "action": "BUY",
        "qty": 1,
        "price": 100
    }]

    with patch('option_auditor.main_analyzer.ManualInputParser') as MockParser:
        mock_parser = MagicMock()
        MockParser.return_value = mock_parser

        mock_parser.parse.return_value = pd.DataFrame({
            "contract_id": ["C1"],
            "symbol": ["AAPL"],
            "datetime": [pd.Timestamp("2023-01-01 10:00:00")],
            "qty": [1],
            "price": [100],
            "fees": [1.0],
            "proceeds": [-100],
            "expiry": [pd.NaT],
            "strike": [None],
            "right": [None]
        })

        mock_build.return_value = []

        res = analyze_csv(None, "auto", manual_data=manual_data)
        assert "error" not in res
        assert "metrics" in res
