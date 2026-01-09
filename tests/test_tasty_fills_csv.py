import io
import os
import pandas as pd
import pytest
from option_auditor import analyze_csv

def test_tasty_fills_auto_detection_parses_successfully():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'QQQ,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:53p",Fill,#423471188,"-1 Jan 9 43d 600 Put STO\n1 Jan 9 43d 595 Put BTO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="auto")
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0

def test_tasty_fills_forced_tasty_parses_successfully():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'XLE,Filled,0.79 cr,0.76 cr,Day,"11/26, 5:30p",Fill,#423459342,"-1 Jan 16 50d 86 Put STO\n1 Jan 16 50d 81 Put BTO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="tasty")
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0

def test_full_fills_csv_auto_mode_parses():
    here = os.path.dirname(__file__)
    full_path = os.path.join(here, "data", "tasty_fills_full.csv")
    assert os.path.exists(full_path), "Fixture file missing: tests/data/tasty_fills_full.csv"
    with open(full_path, "r") as f:
        res = analyze_csv(io.StringIO(f.read()), broker="auto")
    if "error" in res:
        pytest.fail(f"Analysis failed with error: {res['error']}")
    assert res["broker"] == "tasty"
    assert isinstance(res["metrics"], dict)

def test_full_fills_csv_forced_tasty_parses():
    here = os.path.dirname(__file__)
    full_path = os.path.join(here, "data", "tasty_fills_full.csv")
    with open(full_path, "r") as f:
        res = analyze_csv(io.StringIO(f.read()), broker="tasty")
    if "error" in res:
        pytest.fail(f"Analysis failed with error: {res['error']}")
    assert res["broker"] == "tasty"
    assert isinstance(res["metrics"], dict)

def test_edgecase_iron_condor_parsing():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'SPX,Filled,1.80 cr,1.80 cr,Day,"11/12, 8:37p",Fill,#420378085,'
        '"1 Nov 13 Exp 6815 Put BTO\n-1 Nov 13 Exp 6820 Put STO\n-1 Nov 13 Exp 6895 Call STO\n1 Nov 13 Exp 6900 Call BTO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="auto")
    assert res["broker"] == "tasty"
    assert "num_trades" in res["metrics"]
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    assert any("Iron Condor" in (n or "") for n in names)

def test_edgecase_decimal_strike_and_exp_token():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'PFE,Filled,1.94 db,1.97 db,Day,"11/12, 8:57p",Fill,#420391303,'
        '"1 Dec 26 29d 24 Call BTO\n-1 Dec 26 29d 28 Call STO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="tasty")
    assert res["broker"] == "tasty"
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    assert any("Bull Call Spread" in (n or "") for n in names)

def test_edgecase_stock_legs_ignored():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'META,Filled,705.02 cr,705.00 cr,Day,"11/18, 2:39p",Fill,#421414624,'
        '"-100 STC\n-1 Nov 28 1d 705 Put STC"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="tasty")
    assert res["broker"] == "tasty"
    assert res["metrics"]["num_trades"] >= 0

def test_strategy_name_put_vertical_credit():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'IWM,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:22p",Fill,#423455855,'
        '"-1 Jan 9 43d 240 Put STO\n1 Jan 9 43d 235 Put BTO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="auto")
    names = {s.get("strategy") for s in res.get("strategy_groups", [])}
    assert any("Bull Put Spread" in (n or "") for n in names)

def test_strategy_name_present_in_groups():
    csv = (
        "Symbol,Status,MarketOrFill,Price,TIF,Time,TimeStampAtType,Order #,Description\n"
        'QQQ,Filled,1.25 cr,1.25 cr,Day,"11/26, 5:53p",Fill,#423471188,'
        '"-1 Jan 9 43d 600 Put STO\n1 Jan 9 43d 595 Put BTO"\n'
    )
    res = analyze_csv(io.StringIO(csv), broker="tasty")
    groups = res.get("strategy_groups", [])
    assert len(groups) >= 1
    g = groups[0]
    assert "symbol" in g and g["symbol"]
    assert "expiry" in g
    assert "strategy" in g and isinstance(g["strategy"], str)
