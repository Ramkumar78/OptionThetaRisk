import pytest
from unittest.mock import patch, MagicMock
import json
import io

def test_download_pdf_success(client):
    """Test /download/<token>/report.pdf success."""

    # Mock data to be returned by storage.get_report
    mock_report_data = {
        "metrics": {"total_pnl": 1000},
        "verdict": "Green",
        "discipline_score": 90
    }
    mock_json_bytes = json.dumps(mock_report_data).encode('utf-8')

    with patch('webapp.blueprints.analysis_routes.get_db') as mock_get_db:
        mock_storage = MagicMock()
        mock_get_db.return_value = mock_storage

        # storage.get_report called with "report.json" returns the JSON bytes
        def side_effect(token, filename):
            if filename == "report.json":
                return mock_json_bytes
            return None

        mock_storage.get_report.side_effect = side_effect

        # Call the endpoint
        response = client.get('/download/test_token/report.pdf')

        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert response.headers['Content-Disposition'] == 'attachment; filename=Trade_Audit_Report.pdf'
        assert response.data.startswith(b"%PDF")

def test_download_pdf_not_found(client):
    """Test /download/<token>/report.pdf when report.json is missing."""

    with patch('webapp.blueprints.analysis_routes.get_db') as mock_get_db:
        mock_storage = MagicMock()
        mock_get_db.return_value = mock_storage
        mock_storage.get_report.return_value = None

        response = client.get('/download/missing_token/report.pdf')

        assert response.status_code == 404
        assert b"Report not found" in response.data

def test_download_pdf_generation_error(client):
    """Test /download/<token>/report.pdf when generation fails."""

    # Invalid JSON to cause error or just mock the generator to raise exception
    mock_json_bytes = b"invalid json"

    with patch('webapp.blueprints.analysis_routes.get_db') as mock_get_db:
        mock_storage = MagicMock()
        mock_get_db.return_value = mock_storage
        mock_storage.get_report.return_value = mock_json_bytes

        # Since json.loads will fail, it should trigger the exception block
        response = client.get('/download/test_token/report.pdf')

        assert response.status_code == 500
        assert b"Error generating PDF" in response.data
