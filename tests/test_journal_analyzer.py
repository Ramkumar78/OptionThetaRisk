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
    # Wait, logic is: worst_pattern_row = valid_patterns.sort_values(by=['total_pnl'], ascending=True).iloc[0]
    # Iron Condor ($50) < Vertical Spread ($200), so Iron Condor is "worst" relative to others, or just the lowest PnL.
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
