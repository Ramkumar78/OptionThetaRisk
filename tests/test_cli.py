import pytest
from unittest.mock import patch, MagicMock
from option_auditor import cli

def test_cli_main(capsys, tmp_path):
    # Create a dummy CSV file for testing
    csv_content = """Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type
2025-01-01 10:00,AAPL,1,Buy to Open,1.0,0.5,2025-02-21,150,Call
2025-01-02 10:00,AAPL,1,Sell to Close,2.0,0.5,2025-02-21,150,Call
"""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(csv_content)

    # Run the CLI with the dummy CSV
    ret = cli.main(argv=['--csv', str(csv_path)])

    # Capture the output and check for expected strings
    captured = capsys.readouterr()
    assert "PORTFOLIO AUDIT" in captured.out
    assert "PERFORMANCE BY TICKER" in captured.out
    assert "AAPL" in captured.out
    assert ret == 0

def test_cli_error(capsys, tmp_path):
    # Create a dummy CSV file for testing
    csv_path = tmp_path / "error.csv"
    csv_path.write_text("invalid,csv,content")

    # Run the CLI with the dummy CSV that will cause an error
    ret = cli.main(argv=['--csv', str(csv_path)])

    # Capture the output and check for the error message
    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert ret == 1

@patch('option_auditor.cli.main')
def test_cli_entry_point(mock_main):
    with patch('sys.argv', ['option_auditor', '--csv', 'dummy.csv']):
        cli.run_main()
        mock_main.assert_called_once()
