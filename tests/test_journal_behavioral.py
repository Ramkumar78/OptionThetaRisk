import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.journal_analyzer import analyze_journal
from option_auditor.config import BACKTEST_INITIAL_CAPITAL

def test_size_tilting_detection():
    entries = [
        # Trade 1: Loss
        {
            "entry_date": "2023-01-01", "entry_time": "10:00",
            "exit_date": "2023-01-01", "exit_time": "10:30",
            "symbol": "TILT", "qty": 10, "pnl": -100
        },
        # Trade 2: Revenge (Loss + <30m gap) + Size Tilt (>1.5x qty)
        {
            "entry_date": "2023-01-01", "entry_time": "10:45", # 15 min gap
            "exit_date": "2023-01-01", "exit_time": "11:00",
            "symbol": "TILT", "qty": 20, "pnl": -100 # 2x size
        }
    ]

    result = analyze_journal(entries)

    # Check for specific warning text
    suggestions = " ".join(result['suggestions'])
    assert "Size Tilting Warning" in suggestions
    assert "Revenge Trading Warning" in suggestions

def test_no_size_tilting_if_gap_too_long():
    entries = [
        # Trade 1: Loss
        {
            "entry_date": "2023-01-01", "entry_time": "10:00",
            "exit_date": "2023-01-01", "exit_time": "10:30",
            "symbol": "TILT", "qty": 10, "pnl": -100
        },
        # Trade 2: Size increased, but gap > 30 mins
        {
            "entry_date": "2023-01-01", "entry_time": "12:00", # 90 min gap
            "exit_date": "2023-01-01", "exit_time": "12:30",
            "symbol": "TILT", "qty": 20, "pnl": 100
        }
    ]

    result = analyze_journal(entries)
    suggestions = " ".join(result['suggestions'])
    assert "Size Tilting Warning" not in suggestions

def test_discipline_score_perfect():
    # Capital 10000. 1% risk = 100.
    entries = [
        {"entry_date": "2023-01-01", "qty": 1, "pnl": 50},  # Win
        {"entry_date": "2023-01-02", "qty": 1, "pnl": -50}, # Loss within limit
        {"entry_date": "2023-01-03", "qty": 1, "pnl": -90}  # Loss within limit
    ]
    result = analyze_journal(entries)
    assert result['discipline_score'] == 100.0

def test_discipline_score_violation():
    # Capital 10000. 1% risk = 100.
    entries = [
        {"entry_date": "2023-01-01", "qty": 1, "pnl": -200}, # Violation (2%)
        {"entry_date": "2023-01-02", "qty": 1, "pnl": 50},   # Win
        {"entry_date": "2023-01-03", "qty": 1, "pnl": -50},  # Safe Loss
        {"entry_date": "2023-01-04", "qty": 1, "pnl": -150}  # Violation
    ]
    # Total 4 trades. 2 violations. Score = 50%.
    # Note: Capital changes.
    # T1: Bal 10000. Limit 100. Loss 200 > 100. Violated. Bal -> 9800.
    # T2: Bal 9800. Win 50. Bal -> 9850.
    # T3: Bal 9850. Limit 98.5. Loss 50 < 98.5. Safe. Bal -> 9800.
    # T4: Bal 9800. Limit 98. Loss 150 > 98. Violated. Bal -> 9650.

    result = analyze_journal(entries)
    assert result['discipline_score'] == 50.0
    suggestions = " ".join(result['suggestions'])
    assert "Discipline Alert" in suggestions

@patch('option_auditor.journal_analyzer.get_cached_market_data')
def test_fomo_detection(mock_get_data):
    # Setup Mock Data
    dates = pd.date_range(start="2023-01-01", periods=50, freq='B')

    # Constant 100, then spike to 200 ONLY at the entry point to keep Vol low before it.
    # If we have mixed 100s and 200s in the window, StdDev increases, widening the bands.
    # Strategy: 49 days of 100, then 200 on day 50.

    prices = [100.0] * 49 + [200.0]
    data = pd.DataFrame({
        'Close': prices
    }, index=dates)

    # Mock return value
    # Journal analyzer expects a DF. If single symbol, it checks 'Close'.
    mock_get_data.return_value = pd.concat({ "FOMO": data }, axis=1) # Mimic MultiIndex with symbol level

    entries = [
        # Entry during the spike (last index)
        {
            "entry_date": dates[-1].strftime("%Y-%m-%d"),
            "symbol": "FOMO",
            "qty": 1,
            "pnl": 0
        }
    ]

    result = analyze_journal(entries)

    # Check calls
    mock_get_data.assert_called_once()

    # Check result
    suggestions = " ".join(result['suggestions'])
    assert "FOMO Warning" in suggestions
