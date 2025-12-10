import pytest
from option_auditor import journal_analyzer
from datetime import datetime

def test_analyze_journal_empty():
    res = journal_analyzer.analyze_journal([])
    assert res["total_pnl"] == 0.0
    # "symbols" is not returned in empty state, only total_trades etc.
    assert res["total_trades"] == 0

def test_analyze_journal_basic():
    entries = [
        {
            "symbol": "AAPL",
            "pnl": 100.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:00",
            "strategy": "Long Call",
            "direction": "LONG",
            "qty": 1.0,
            "entry_price": 100.0,
            "exit_price": 110.0
        },
        {
            "symbol": "AAPL",
            "pnl": -50.0,
            "entry_date": "2023-01-02",
            "entry_time": "10:00",
            "strategy": "Long Call",
            "direction": "LONG",
            "qty": 1.0
        },
        {
            "symbol": "MSFT",
            "pnl": 200.0,
            "entry_date": "2023-01-03",
            "entry_time": "12:00",
            "strategy": "Short Put"
        }
    ]

    res = journal_analyzer.analyze_journal(entries)

    assert res["total_pnl"] == 250.0
    assert res["total_trades"] == 3
    assert res["win_rate"] == 66.7 # Rounded

    # Check Patterns
    patterns = res["patterns"]
    assert len(patterns) > 0
    aapl_strat = next(p for p in patterns if p["strategy"] == "Long Call")
    assert aapl_strat["count"] == 2
    assert aapl_strat["total_pnl"] == 50.0

def test_analyze_journal_time_buckets():
    entries = [
        {"pnl": 10, "entry_time": "09:30", "strategy": "A"},
        {"pnl": 10, "entry_time": "15:00", "strategy": "B"}
    ]
    res = journal_analyzer.analyze_journal(entries)

    time_stats = res["time_analysis"]
    # Check if we have buckets
    buckets = [t["time_bucket"] for t in time_stats]
    assert "Opening (9:30-10:30)" in buckets
    assert "Afternoon (2:00-4:00)" in buckets

def test_analyze_journal_filters():
    # If the function supported filters we would test them here.
    # Currently it takes raw list.
    pass
