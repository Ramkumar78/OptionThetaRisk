import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
from option_auditor.cli import main, _format_pnl

def test_format_pnl():
    assert "\033[92m" in _format_pnl(100)
    assert "\033[91m" in _format_pnl(-100)

@patch('option_auditor.cli.analyze_csv')
@patch('sys.stdout', new_callable=StringIO)
def test_main_audit_csv(mock_stdout, mock_analyze_csv):
    # Mock return value
    mock_analyze_csv.return_value = {
        "verdict": "GOOD",
        "metrics": {"avg_hold_days": 5},
        "strategy_metrics": {
            "num_trades": 10,
            "win_rate": 0.6,
            "total_pnl": 1000.0,
            "total_fees": 10.0
        },
        "leakage_report": {"efficiency_ratio": 1.2},
        "symbols": [
            {"symbol": "AAPL", "pnl": 500, "win_rate": 0.8}
        ]
    }

    ret = main(["--csv", "test.csv"])

    assert ret == 0
    output = mock_stdout.getvalue()
    assert "PORTFOLIO AUDIT" in output
    assert "$1,000.00" in output
    assert "AAPL" in output

@patch('option_auditor.cli.analyze_csv')
@patch('sys.stdout', new_callable=StringIO)
def test_main_audit_csv_error(mock_stdout, mock_analyze_csv):
    mock_analyze_csv.return_value = {"error": "File not found"}

    ret = main(["--csv", "test.csv"])

    assert ret == 1
    assert "Error: File not found" in mock_stdout.getvalue()

@patch('option_auditor.cli.screen_bull_put_spreads')
@patch('sys.stdout', new_callable=StringIO)
def test_main_screener_bull_put(mock_stdout, mock_screen):
    mock_screen.return_value = [
        {
            "ticker": "TSLA",
            "price": 200.0,
            "expiry": "2023-12-15",
            "dte": 45,
            "short_strike": 180,
            "long_strike": 175,
            "credit": 1.5,
            "roi_pct": 10.0,
            "short_delta": -0.30
        }
    ]

    ret = main(["--strategy", "bull_put"])

    assert ret == 0
    output = mock_stdout.getvalue()
    assert "Scanning for Bull Put Spreads" in output
    assert "TSLA" in output
    assert "180/175" in output

@patch('option_auditor.cli.screen_bull_put_spreads')
@patch('sys.stdout', new_callable=StringIO)
def test_main_screener_no_results(mock_stdout, mock_screen):
    mock_screen.return_value = []

    ret = main(["--strategy", "bull_put"])

    assert ret == 0
    assert "No setups found" in mock_stdout.getvalue()

@patch('sys.stderr', new_callable=StringIO)
def test_main_no_args(mock_stderr):
    # expect exit code 2 usually for argparse error
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code != 0
