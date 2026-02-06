import pytest
from option_auditor.journal_analyzer import analyze_journal

def test_analyze_journal_empty():
    """Test that analyzing an empty journal returns zeroed stats."""
    result = analyze_journal([])
    assert result["total_trades"] == 0
    assert result["win_rate"] == 0
    assert result["total_pnl"] == 0.0
    assert result["best_pattern"] == "None"
    assert result["worst_pattern"] == "None"
    assert len(result["suggestions"]) == 0
    assert result["equity_curve"] == []

def test_analyze_journal_basic():
    """Test basic analysis with mixed trades."""
    entries = [
        {"strategy": "Iron Condor", "pnl": 100.0, "entry_time": "10:00"},
        {"strategy": "Iron Condor", "pnl": -50.0, "entry_time": "10:15"},
        {"strategy": "Vertical Spread", "pnl": 200.0, "entry_time": "14:30"},
    ]
    result = analyze_journal(entries)

    assert result["total_trades"] == 3
    assert result["total_pnl"] == 250.0
    # Win rate: 2 wins out of 3 = 66.66%
    assert result["win_rate"] == 66.7

    # Patterns
    # Iron Condor: 1 win, 1 loss. WR 50%. Total $50.
    # Vertical Spread: 1 win. WR 100%. Total $200.

    # Best pattern should be Vertical Spread (sorted by total_pnl, then win_rate)
    assert "Vertical Spread" in result["best_pattern"]

    # Worst pattern should be Iron Condor (Total $50 < $200)
    assert "Iron Condor" in result["worst_pattern"]

def test_analyze_journal_time_buckets():
    """Test that time buckets are correctly assigned."""
    entries = [
        {"strategy": "A", "pnl": 10, "entry_time": "09:45"}, # Opening (<10:30)
        {"strategy": "A", "pnl": 10, "entry_time": "11:00"}, # Morning (<12:00)
        {"strategy": "A", "pnl": 10, "entry_time": "13:00"}, # Midday (<14:00)
        {"strategy": "A", "pnl": 10, "entry_time": "15:00"}, # Afternoon (<16:00)
        {"strategy": "A", "pnl": 10, "entry_time": "16:30"}, # After Hours
    ]
    result = analyze_journal(entries)

    # Check if time_analysis has entries for these buckets
    buckets = {item['time_bucket'] for item in result['time_analysis']}
    assert "Opening (9:30-10:30)" in buckets
    assert "Morning (10:30-12:00)" in buckets
    assert "Midday (12:00-2:00)" in buckets
    assert "Afternoon (2:00-4:00)" in buckets
    assert "After Hours" in buckets

def test_analyze_journal_suggestions():
    """Test generation of suggestions based on win rates."""
    entries = [
        # Strategy A: High Win Rate, Profitable -> Keep trading
        {"strategy": "Strategy A", "pnl": 100, "entry_time": "10:00"},
        {"strategy": "Strategy A", "pnl": 100, "entry_time": "10:00"},
        {"strategy": "Strategy A", "pnl": 100, "entry_time": "10:00"},

        # Strategy B: Low Win Rate -> Review
        {"strategy": "Strategy B", "pnl": -100, "entry_time": "10:00"},
        {"strategy": "Strategy B", "pnl": -100, "entry_time": "10:00"},
        {"strategy": "Strategy B", "pnl": -100, "entry_time": "10:00"},
    ]
    result = analyze_journal(entries)

    suggestions_text = " ".join(result["suggestions"])
    assert "Keep trading <b>Strategy A</b>" in suggestions_text
    assert "Review <b>Strategy B</b>" in suggestions_text

def test_analyze_journal_invalid_time():
    """Test handling of invalid or missing time formats."""
    entries = [
        {"strategy": "A", "pnl": 10, "entry_time": "invalid"},
        {"strategy": "A", "pnl": 10, "entry_time": ""},
        {"strategy": "A", "pnl": 10, "entry_time": None},
    ]
    result = analyze_journal(entries)

    buckets = {item['time_bucket'] for item in result['time_analysis']}
    assert "Unknown" in buckets

def test_analyze_journal_equity_curve():
    """Test equity curve calculation and sorting."""
    # Unsorted input
    entries = [
        {"strategy": "A", "pnl": 100, "entry_date": "2023-01-02", "entry_time": "10:00"},
        {"strategy": "A", "pnl": 50, "entry_date": "2023-01-01", "entry_time": "10:00"}, # Should be first
        {"strategy": "B", "pnl": -20, "entry_date": "2023-01-03", "entry_time": "10:00"},
    ]
    result = analyze_journal(entries)

    curve = result["equity_curve"]
    assert len(curve) == 3

    # Check sorting
    assert curve[0]['date'].startswith("2023-01-01")
    assert curve[1]['date'].startswith("2023-01-02")
    assert curve[2]['date'].startswith("2023-01-03")

    # Check cumulative PnL
    # 1. 2023-01-01: +50 -> Cum: 50
    # 2. 2023-01-02: +100 -> Cum: 150
    # 3. 2023-01-03: -20 -> Cum: 130
    assert curve[0]['cumulative_pnl'] == 50.0
    assert curve[1]['cumulative_pnl'] == 150.0
    assert curve[2]['cumulative_pnl'] == 130.0

def test_analyze_journal_equity_curve_fallback():
    """Test equity curve handles missing dates by falling back gracefully (not crashing)."""
    entries = [
        {"strategy": "A", "pnl": 100}, # Missing date/time
        {"strategy": "A", "pnl": 50},
    ]
    result = analyze_journal(entries)

    # Should not crash, and return a curve (based on default date/time filling)
    assert len(result["equity_curve"]) == 2
    # Logic fills with datetime.now(), sorting might be unstable if times are identical "00:00", but it works.

def test_equity_curve_sorting_and_stability():
    """Test equity curve sorting with identical timestamps and unsorted input."""
    entries = [
        {"strategy": "A", "pnl": 10, "entry_date": "2023-01-01", "entry_time": "12:00"},
        {"strategy": "A", "pnl": 20, "entry_date": "2023-01-01", "entry_time": "10:00"}, # Earlier same day
        {"strategy": "A", "pnl": 30, "entry_date": "2023-01-01", "entry_time": "12:00"}, # Same time as first
    ]

    result = analyze_journal(entries)
    curve = result["equity_curve"]

    assert len(curve) == 3
    # Check 10:00 is first
    assert "10:00" in curve[0]['date']
    assert curve[0]['cumulative_pnl'] == 20.0

    # Check 12:00 entries
    # Pandas sort is stable. The original order of index 0 and 2 (relative to each other) should be preserved.
    # Entry 0 (+10) comes before Entry 2 (+30)
    assert curve[1]['cumulative_pnl'] == 30.0 # 20 + 10
    assert curve[2]['cumulative_pnl'] == 60.0 # 30 + 30

def test_equity_curve_invalid_data():
    """Test equity curve generation with non-numeric PnL and invalid dates."""
    entries = [
        {"strategy": "A", "pnl": "invalid", "entry_date": "bad-date", "entry_time": "bad-time"},
        {"strategy": "A", "pnl": "50.5", "entry_date": "2023-01-01", "entry_time": "10:00"},
    ]

    result = analyze_journal(entries)
    curve = result["equity_curve"]

    assert len(curve) == 2

    # "invalid" pnl should be 0.0 (coerced)
    # "bad-date" causes fallback to datetime.now() -> end of list (after 2023)

    # 2023 entry should be first
    entry_2023 = next(p for p in curve if "2023-01-01" in p['date'])
    assert entry_2023['cumulative_pnl'] == 50.5

    # The invalid entry is effectively 0 pnl
    # If it is after, cum pnl stays 50.5.
    assert result['total_pnl'] == 50.5

def test_equity_curve_single_entry():
    """Test equity curve with a single entry."""
    entries = [
        {"strategy": "A", "pnl": 100, "entry_date": "2023-01-01"}
    ]
    result = analyze_journal(entries)
    curve = result["equity_curve"]
    assert len(curve) == 1
    assert curve[0]['cumulative_pnl'] == 100.0

def test_analyze_journal_overtrading_alert():
    """Test detection of over-trading (300% increase in volume vs 30-day average)."""
    # Create 30 days of consistent low volume (1 trade per day)
    entries = []
    # Previous 30 days: 2023-01-01 to 2023-01-30
    for i in range(1, 31):
        day = f"{i:02d}"
        entries.append({"strategy": "A", "pnl": 10, "entry_date": f"2023-01-{day}", "entry_time": "10:00"})

    # 31st day: High volume (5 trades)
    # Average of prev 30 is 1.0. 300% increase means >= 4.0. 5 >= 4.
    for _ in range(5):
        entries.append({"strategy": "A", "pnl": 10, "entry_date": "2023-01-31", "entry_time": "10:00"})

    result = analyze_journal(entries)

    assert result["psychology_alert"] is not None
    assert "Over-trading Detected" in result["psychology_alert"]
    assert "Volume (5)" in result["psychology_alert"]
    assert "average (1.0)" in result["psychology_alert"]

def test_analyze_journal_no_overtrading_alert():
    """Test that normal volume increase does not trigger alert."""
    entries = []
    # Previous 30 days: 1 trade per day
    for i in range(1, 31):
        day = f"{i:02d}"
        entries.append({"strategy": "A", "pnl": 10, "entry_date": f"2023-01-{day}", "entry_time": "10:00"})

    # 31st day: Moderate volume (3 trades)
    # Average 1.0. 3 trades is 200% increase (3x). Alert threshold is 4x (300% increase).
    for _ in range(3):
        entries.append({"strategy": "A", "pnl": 10, "entry_date": "2023-01-31", "entry_time": "10:00"})

    result = analyze_journal(entries)

    assert result["psychology_alert"] is None
