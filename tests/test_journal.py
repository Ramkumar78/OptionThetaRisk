import pytest
from option_auditor.journal_analyzer import analyze_journal

def test_analyze_journal_empty():
    res = analyze_journal([])
    assert res['total_trades'] == 0
    assert res['win_rate'] == 0
    assert res['suggestions'] == []

def test_analyze_journal_basic():
    entries = [
        {"strategy": "Iron Condor", "entry_time": "09:45", "pnl": 100, "win": True},
        {"strategy": "Iron Condor", "entry_time": "10:00", "pnl": 50, "win": True},
        {"strategy": "Iron Condor", "entry_time": "12:00", "pnl": -200, "win": False},
        {"strategy": "Bull Flag", "entry_time": "09:50", "pnl": 150, "win": True},
        {"strategy": "Bull Flag", "entry_time": "14:00", "pnl": 150, "win": True},
    ]
    res = analyze_journal(entries)

    assert res['total_trades'] == 5
    # Iron Condor: 2 Wins, 1 Loss. Total PnL: -50. WR: 66%
    # Bull Flag: 2 Wins. Total PnL: 300. WR: 100%

    assert res['best_pattern'].startswith("Bull Flag")
    assert "Bull Flag" in res['best_pattern']
    assert "100.0%" in res['best_pattern']

    # Time Analysis
    # 09:45 -> Opening
    # 09:50 -> Opening
    # 10:00 -> Opening
    # 12:00 -> Midday
    # 14:00 -> Afternoon

    # Opening: 3 trades, 3 wins (100%)
    assert "Opening" in res['best_time']

    # Suggestions
    # Should suggest keeping Bull Flag
    found_bull = False
    for s in res['suggestions']:
        if "Bull Flag" in s and "Keep trading" in s:
            found_bull = True
    # Actually count requirement is >= 3 for pattern suggestions in my code?
    # Let's check code. Yes "if row['count'] >= 3:".
    # Iron Condor has 3 trades. WR 66%, PnL -50.
    # Logic: avg_pnl < 0 -> "is losing money despite..."

    found_ic_warning = False
    for s in res['suggestions']:
        if "Iron Condor" in s and "losing money" in s:
            found_ic_warning = True

    assert found_ic_warning

def test_analyze_journal_time_buckets():
    entries = [
        {"strategy": "A", "entry_time": "09:30", "pnl": 10}, # Opening
        {"strategy": "A", "entry_time": "10:29", "pnl": 10}, # Opening
        {"strategy": "A", "entry_time": "10:31", "pnl": 10}, # Morning
        {"strategy": "A", "entry_time": "12:01", "pnl": 10}, # Midday
        {"strategy": "A", "entry_time": "14:01", "pnl": 10}, # Afternoon
        {"strategy": "A", "entry_time": "16:01", "pnl": 10}, # After Hours
    ]
    res = analyze_journal(entries)
    time_stats = {r['time_bucket']: r['count'] for r in res['time_analysis']}

    assert time_stats.get("Opening (9:30-10:30)") == 2
    assert time_stats.get("Morning (10:30-12:00)") == 1
    assert time_stats.get("Midday (12:00-2:00)") == 1
    assert time_stats.get("Afternoon (2:00-4:00)") == 1
    assert time_stats.get("After Hours") == 1
