import pytest
from datetime import datetime, timedelta
from option_auditor.journal_analyzer import analyze_journal

def test_overtrading_alert_detection():
    """
    Test the 'Over-trading' alert by providing a trade list where the last day's volume is >400% of the average.
    Logic: last_day_vol >= (avg_vol * 4.0)
    """
    entries = []
    base_date = datetime(2023, 1, 1)

    # create 30 days of 1 trade per day
    for i in range(30):
        d = (base_date + timedelta(days=i)).date().isoformat()
        entries.append({
            "strategy": "Vertical",
            "pnl": 10.0,
            "entry_date": d,
            "entry_time": "10:00"
        })

    # create 1 day (the last day) with 5 trades
    last_day = (base_date + timedelta(days=30)).date().isoformat()
    for _ in range(5):
        entries.append({
            "strategy": "Vertical",
            "pnl": 10.0,
            "entry_date": last_day,
            "entry_time": "10:00"
        })

    # Analyze
    result = analyze_journal(entries)

    # Verify Alert
    # 5 trades vs avg 1.0 -> 500% -> Should trigger
    assert result["psychology_alert"] is not None
    assert "Over-trading Detected" in result["psychology_alert"]
    # The message says: Volume (5) is >300% of 30-day average (1.0).
    # 300% increase means 4x multiplier.
    assert "Volume (5)" in result["psychology_alert"]

def test_fee_erosion_calculation():
    """
    Verify the 'Fee Erosion' calculation (total fees / gross profit).
    Logic: if total_fees / total_gross_pnl > 0.15 -> Warning
    """
    entries = [
        # Gross PnL = Net PnL + Fees
        # We want Fees / Gross > 0.15
        # Let Gross = 100.0
        # Let Fees = 16.0
        # Net PnL = 84.0
        # Ratio = 16 / 100 = 0.16 (16%)
        {
            "strategy": "Iron Condor",
            "pnl": 84.0,   # Net PnL
            "fees": 16.0,  # Fees
            "entry_date": "2023-01-01",
            "entry_time": "10:00"
        }
    ]

    result = analyze_journal(entries)
    suggestions = result["suggestions"]

    # Check for warning
    found_warning = any("Fee Erosion Warning" in s for s in suggestions)
    assert found_warning, f"Expected Fee Erosion Warning in suggestions: {suggestions}"

    # Check the percentage calculation in the message
    # "16.0% of your Gross Profit"
    warning_msg = next(s for s in suggestions if "Fee Erosion Warning" in s)
    assert "16.0%" in warning_msg

def test_red_monday_analysis():
    """
    Test the 'Day of Week' analysis to ensure it correctly identifies 'Red Mondays.'
    Logic: Monday PnL < 0 AND Monday PnL == min(all_days_pnl)
    """
    entries = [
        # Monday (2023-10-02) -> Loss -100
        {"strategy": "A", "pnl": -100.0, "entry_date": "2023-10-02"},
        # Tuesday (2023-10-03) -> Loss -50 (better than Monday)
        {"strategy": "A", "pnl": -50.0, "entry_date": "2023-10-03"},
        # Wednesday (2023-10-04) -> Win 50
        {"strategy": "A", "pnl": 50.0, "entry_date": "2023-10-04"},
    ]

    result = analyze_journal(entries)
    suggestions = result["suggestions"]

    # Check for Red Day Analysis
    found_red_day = any("Red Day Analysis" in s for s in suggestions)
    assert found_red_day, f"Expected Red Day Analysis in suggestions: {suggestions}"

    red_day_msg = next(s for s in suggestions if "Red Day Analysis" in s)
    assert "lose most on Mondays" in red_day_msg

def test_red_monday_not_worst_day():
    """
    Ensure Red Monday is NOT flagged if it's not the worst day.
    """
    entries = [
        # Monday (2023-10-02) -> Loss -50
        {"strategy": "A", "pnl": -50.0, "entry_date": "2023-10-02"},
        # Tuesday (2023-10-03) -> Loss -100 (Worse than Monday)
        {"strategy": "A", "pnl": -100.0, "entry_date": "2023-10-03"},
    ]

    result = analyze_journal(entries)
    suggestions = result["suggestions"]

    # Should NOT have Red Day Analysis for Monday
    found_red_day = any("Red Day Analysis" in s and "Mondays" in s for s in suggestions)
    assert not found_red_day, "Should not flag Monday if Tuesday is worse"
