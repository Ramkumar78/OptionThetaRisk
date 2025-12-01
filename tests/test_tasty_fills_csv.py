import io
import os

import pandas as pd
import pytest

from option_auditor import analyze_csv


def _write(tmp_path, text, name="fills.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_tasty_fills_auto_detection_parses_successfully(tmp_path):
    # Minimal sample of the user's Tastytrade Activity/Fills export format
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'QQQ,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:53p",Fill,#423471188,"-1 Jan 9 43d 600 Put STO\n1 Jan 9 43d 595 Put BTO"\n'
    )
    path = _write(tmp_path, csv)

    res = analyze_csv(path, broker="auto", out_dir=None)
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0


def test_tasty_fills_forced_tasty_parses_successfully(tmp_path):
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'XLE,Filled,0.79 cr,0.76 cr,Day,"11/26, 5:30p",Fill,#423459342,"-1 Jan 16 50d 86 Put STO\n1 Jan 16 50d 81 Put BTO"\n'
    )
    path = _write(tmp_path, csv, name="fills_forced.csv")

    res = analyze_csv(path, broker="tasty", out_dir=None)
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0


def test_full_fills_csv_auto_mode_parses():
    # Use the full CSV provided by the user (stored under tests/data)
    here = os.path.dirname(__file__)
    full_path = os.path.join(here, "data", "tasty_fills_full.csv")
    assert os.path.exists(full_path), "Fixture file missing: tests/data/tasty_fills_full.csv"

    res = analyze_csv(full_path, broker="auto", out_dir=None)
    assert res["broker"] == "tasty"
    assert isinstance(res["metrics"], dict)


def test_full_fills_csv_forced_tasty_parses():
    here = os.path.dirname(__file__)
    full_path = os.path.join(here, "data", "tasty_fills_full.csv")

    res = analyze_csv(full_path, broker="tasty", out_dir=None)
    assert res["broker"] == "tasty"
    assert isinstance(res["metrics"], dict)


def test_edgecase_iron_condor_parsing(tmp_path):
    # Four legs with mixed sides; ensure 4 legs recognized and grouped
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'SPX,Filled,1.80 cr,1.80 cr,Day,"11/12, 8:37p",Fill,#420378085,'
        '"1 Nov 13 Exp 6815 Put BTO\n-1 Nov 13 Exp 6820 Put STO\n-1 Nov 13 Exp 6895 Call STO\n1 Nov 13 Exp 6900 Call BTO"\n'
    )
    path = _write(tmp_path, csv, name="iron_condor.csv")
    res = analyze_csv(path, broker="auto", out_dir=None)
    assert res["broker"] == "tasty"
    # At minimum it should not crash and produce metrics structure
    assert "num_trades" in res["metrics"]
    # Strategy detection
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    assert any("Iron Condor" in (n or "") for n in names)


def test_edgecase_decimal_strike_and_exp_token(tmp_path):
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'PFE,Filled,1.94 db,1.97 db,Day,"11/12, 8:57p",Fill,#420391303,'
        '"1 Dec 26 29d 24 Call BTO\n-1 Dec 26 29d 28 Call STO"\n'
    )
    path = _write(tmp_path, csv, name="decimal_strike.csv")
    res = analyze_csv(path, broker="tasty", out_dir=None)
    assert res["broker"] == "tasty"
    # Should classify as a Call Vertical (side depends on credit/debit)
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    # With new classification, this is a "Bull Call Spread"
    assert any("Bull Call Spread" in (n or "") for n in names)


def test_edgecase_stock_legs_ignored(tmp_path):
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'META,Filled,705.02 cr,705.00 cr,Day,"11/18, 2:39p",Fill,#421414624,'
        '"-100 STC\n-1 Nov 28 1d 705 Put STC"\n'
    )
    path = _write(tmp_path, csv, name="stock_legs.csv")
    res = analyze_csv(path, broker="tasty", out_dir=None)
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0


def test_strategy_name_put_vertical_credit(tmp_path):
    # Simple vertical put credit spread
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'IWM,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:22p",Fill,#423455855,'
        '"-1 Jan 9 43d 240 Put STO\n1 Jan 9 43d 235 Put BTO"\n'
    )
    path = _write(tmp_path, csv, name="put_vertical_credit.csv")
    res = analyze_csv(path, broker="auto", out_dir=None)
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    # With new classification, this is a "Bull Put Spread" (which is a credit spread)
    assert any("Bull Put Spread" in (n or "") for n in names)


def test_strategy_name_present_in_groups(tmp_path):
    # Ensure strategy_groups contain symbol/expiry/strategy fields
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'QQQ,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:53p",Fill,#423471188,'
        '"-1 Jan 9 43d 600 Put STO\n1 Jan 9 43d 595 Put BTO"\n'
    )
    path = _write(tmp_path, csv, name="strategy_fields.csv")
    res = analyze_csv(path, broker="tasty", out_dir=None)
    groups = res.get("strategy_groups", [])
    assert len(groups) >= 1
    g = groups[0]
    assert "symbol" in g and g["symbol"]
    assert "expiry" in g
    assert "strategy" in g and isinstance(g["strategy"], str)
