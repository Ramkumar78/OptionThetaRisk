import pytest
from option_auditor.journal_analyzer import analyze_journal

def test_revenge_trading_detection():
    """
    Test that a trade opened within 30 minutes of a loss on the same symbol
    triggers a 'Revenge Trading' suggestion.
    """
    entries = [
        # Trade 1: Loss, Exit at 10:00
        {
            "symbol": "AAPL",
            "pnl": -100.0,
            "entry_date": "2023-01-01",
            "entry_time": "09:00",
            "exit_date": "2023-01-01",
            "exit_time": "10:00"
        },
        # Trade 2: Opens at 10:15 (15 mins later) -> Revenge
        {
            "symbol": "AAPL",
            "pnl": 50.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:15",
            "exit_date": "2023-01-01",
            "exit_time": "11:00"
        }
    ]
    result = analyze_journal(entries)

    # Check if suggestions contain "Revenge Trading"
    suggestions = " ".join(result["suggestions"])
    assert "Revenge Trading" in suggestions, "Should detect revenge trading within 30 mins of loss"

def test_revenge_trading_safe_gap():
    """
    Test that a trade opened AFTER 30 minutes of a loss is NOT flagged.
    """
    entries = [
        # Trade 1: Loss, Exit at 10:00
        {
            "symbol": "AAPL",
            "pnl": -100.0,
            "entry_date": "2023-01-01",
            "entry_time": "09:00",
            "exit_date": "2023-01-01",
            "exit_time": "10:00"
        },
        # Trade 2: Opens at 10:31 (31 mins later) -> Safe
        {
            "symbol": "AAPL",
            "pnl": 50.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:31",
            "exit_date": "2023-01-01",
            "exit_time": "11:00"
        }
    ]
    result = analyze_journal(entries)

    suggestions = " ".join(result["suggestions"])
    assert "Revenge Trading" not in suggestions, "Should not flag trades > 30 mins after loss"

def test_revenge_trading_different_symbol():
    """
    Test that a trade opened shortly after a loss on a DIFFERENT symbol is NOT flagged.
    """
    entries = [
        # Trade 1: Loss on AAPL
        {
            "symbol": "AAPL",
            "pnl": -100.0,
            "entry_date": "2023-01-01",
            "entry_time": "09:00",
            "exit_date": "2023-01-01",
            "exit_time": "10:00"
        },
        # Trade 2: Opens at 10:15 on TSLA -> Safe (assuming different symbol means diff strategy/intent)
        {
            "symbol": "TSLA",
            "pnl": 50.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:15",
            "exit_date": "2023-01-01",
            "exit_time": "11:00"
        }
    ]
    result = analyze_journal(entries)

    suggestions = " ".join(result["suggestions"])
    assert "Revenge Trading" not in suggestions, "Should not flag trades on different symbols"

def test_revenge_trading_previous_win():
    """
    Test that opening a trade shortly after a WIN is NOT flagged as revenge.
    """
    entries = [
        # Trade 1: Win on AAPL
        {
            "symbol": "AAPL",
            "pnl": 100.0,
            "entry_date": "2023-01-01",
            "entry_time": "09:00",
            "exit_date": "2023-01-01",
            "exit_time": "10:00"
        },
        # Trade 2: Opens at 10:15 on AAPL
        {
            "symbol": "AAPL",
            "pnl": 50.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:15",
            "exit_date": "2023-01-01",
            "exit_time": "11:00"
        }
    ]
    result = analyze_journal(entries)

    suggestions = " ".join(result["suggestions"])
    assert "Revenge Trading" not in suggestions, "Should not flag trades after a win"

def test_revenge_trading_missing_exit_time():
    """
    Test that missing exit time does not cause a crash and doesn't trigger false positives.
    """
    entries = [
        # Trade 1: Loss, but NO exit time
        {
            "symbol": "AAPL",
            "pnl": -100.0,
            "entry_date": "2023-01-01",
            "entry_time": "09:00"
            # No exit_date/time
        },
        # Trade 2: Opens later
        {
            "symbol": "AAPL",
            "pnl": 50.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:15"
        }
    ]
    result = analyze_journal(entries)
    # Should run without error
    assert isinstance(result, dict)
    suggestions = " ".join(result["suggestions"])
    assert "Revenge Trading" not in suggestions

def test_fee_auditing_high_fees():
    """
    Test that fees > 15% of Gross Profit trigger a warning.
    """
    entries = [
        # Gross PnL = Net + Fees = 84 + 16 = 100.
        # Fees = 16. Ratio = 16/100 = 16%. Warning triggers if > 15%.
        {
            "symbol": "AAPL",
            "pnl": 84.0, # Net
            "fees": 16.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:00"
        }
    ]
    result = analyze_journal(entries)

    suggestions = " ".join(result["suggestions"])
    assert "Fee Erosion Warning" in suggestions
    assert "16.0% of your Gross Profit" in suggestions

def test_fee_auditing_low_fees():
    """
    Test that fees <= 15% do not trigger a warning.
    """
    entries = [
        # Gross=100. Fees=10. Net=90. Ratio=10%.
        {
            "symbol": "AAPL",
            "pnl": 90.0,
            "fees": 10.0,
            "entry_date": "2023-01-01",
            "entry_time": "10:00"
        }
    ]
    result = analyze_journal(entries)

    suggestions = " ".join(result["suggestions"])
    assert "Fee Erosion Warning" not in suggestions
