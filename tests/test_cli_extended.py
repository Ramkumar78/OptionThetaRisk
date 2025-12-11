import pytest
from unittest.mock import patch, MagicMock
from option_auditor.cli import main
import io

@patch("option_auditor.cli.analyze_csv")
def test_cli_audit_flow(mock_analyze, tmp_path):
    mock_analyze.return_value = {
        "metrics": {"avg_hold_days": 5.0},
        "strategy_metrics": {
            "num_trades": 10,
            "win_rate": 0.5,
            "total_pnl": 100.0,
            "total_fees": 10.0
        },
        "leakage_report": {"efficiency_ratio": 0.9},
        "symbols": [{"symbol": "AAPL", "pnl": 100.0, "win_rate": 1.0}],
        "verdict": "GOOD"
    }

    # Test stdout
    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        ret = main(["--csv", "dummy.csv"])
        assert ret == 0
        output = mock_stdout.getvalue()
        assert "PORTFOLIO AUDIT" in output
        assert "$100.00" in output

@patch("option_auditor.cli.analyze_csv")
def test_cli_audit_error(mock_analyze):
    mock_analyze.return_value = {"error": "Failed to parse"}
    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        ret = main(["--csv", "dummy.csv"])
        assert ret == 1
        assert "Error: Failed to parse" in mock_stdout.getvalue()

@patch("option_auditor.cli.analyze_csv")
def test_cli_output_file(mock_analyze, tmp_path):
    mock_analyze.return_value = {
        "metrics": {"avg_hold_days": 5.0},
        "strategy_metrics": {"num_trades": 0, "win_rate": 0, "total_pnl": 0, "total_fees": 0},
        "leakage_report": {"efficiency_ratio": 0},
        "symbols": [],
        "verdict": "N/A",
        "excel_report": io.BytesIO(b"excel_data")
    }

    out_file = tmp_path / "report.xlsx"
    ret = main(["--csv", "dummy.csv", "--output", str(out_file)])
    assert ret == 0
    assert out_file.exists()
    assert out_file.read_bytes() == b"excel_data"

@patch("option_auditor.cli.screen_bull_put_spreads")
def test_cli_screener(mock_screen):
    # Mock results
    mock_screen.return_value = [{
        "ticker": "AAPL",
        "price": 150.0,
        "expiry": "2023-01-01",
        "dte": 45,
        "short_strike": 140,
        "long_strike": 135,
        "credit": 1.0,
        "roi_pct": 10.0,
        "short_delta": -0.3
    }]

    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        ret = main(["--strategy", "bull_put"])
        assert ret == 0
        output = mock_stdout.getvalue()
        assert "Bull Put Spreads" in output
        assert "AAPL" in output

@patch("option_auditor.cli.screen_bull_put_spreads")
def test_cli_screener_empty(mock_screen):
    mock_screen.return_value = []
    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        ret = main(["--strategy", "bull_put"])
        assert ret == 0
        assert "No setups found" in mock_stdout.getvalue()

def test_cli_missing_args():
    # Should raise SystemExit
    with pytest.raises(SystemExit):
        with patch("sys.stderr", new_callable=io.StringIO): # Suppress stderr
            main([])

def test_format_pnl():
    from option_auditor.cli import _format_pnl, GREEN, RED, RESET
    assert GREEN in _format_pnl(100)
    assert RED in _format_pnl(-100)
