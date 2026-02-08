import pytest
import io
import json
from webapp.reporting_service import generate_trade_audit_pdf
from reportlab.pdfgen import canvas

def test_generate_pdf_structure():
    """Verifies that the PDF generation function runs and produces a valid PDF buffer."""

    # Mock Data matching the structure expected by generate_trade_audit_pdf
    mock_data = {
        "metrics": {
            "total_pnl": 1500.50,
            "win_rate": 0.65,
            "num_trades": 20
        },
        "strategy_metrics": {
            "profit_factor": 1.8,
            "max_drawdown": 200.0,
            "total_pnl": 1500.50
        },
        "verdict": "Green Flag",
        "verdict_color": "green",
        "discipline_score": 85,
        "discipline_details": [
            "+ Cutting Losses Early",
            "- Gamma Risk (<3d)"
        ],
        "portfolio_curve": [
            {"x": "2023-01-01T10:00:00", "y": 0.0},
            {"x": "2023-01-02T10:00:00", "y": 100.0},
            {"x": "2023-01-03T10:00:00", "y": 50.0},
            {"x": "2023-01-04T10:00:00", "y": 200.0}
        ],
        "leakage_report": {
            "fee_drag": 5.0,
            "stale_capital": []
        }
    }

    pdf_buffer = generate_trade_audit_pdf(mock_data)

    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_content = pdf_buffer.getvalue()

    # Basic PDF Magic Number Check
    assert pdf_content.startswith(b"%PDF")

    # Content Checks (simple string search in binary - not robust but good enough for existence)
    # Note: PDF compression might hide text, but reportlab standard font usually visible?
    # Actually, ReportLab compresses streams by default.
    # But we can check if file is not empty and reasonably sized.
    assert len(pdf_content) > 1000

def test_generate_pdf_empty_data():
    """Verifies PDF generation handles missing data gracefully."""
    mock_data = {}

    pdf_buffer = generate_trade_audit_pdf(mock_data)

    assert isinstance(pdf_buffer, io.BytesIO)
    assert pdf_buffer.getvalue().startswith(b"%PDF")
