import io
import os
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


def make_csv_bytes():
    # Minimal tasty CSV content with headers used by _normalize_tasty
    content = (
        "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n"
        "2025-01-01 10:00,MSFT,1,Buy to Open,1.00,0.10,2025-02-21,500,Put\n"
        "2025-01-03 10:00,MSFT,1,Sell to Close,1.50,0.10,2025-02-21,500,Put\n"
    )
    return content.encode("utf-8")


@pytest.fixture()
def app():
    from webapp.app import create_app

    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    # Clean up the reports folder before each test
    report_folder = app.config["REPORT_FOLDER"]
    if os.path.exists(report_folder):
        shutil.rmtree(report_folder, ignore_errors=True)
    os.makedirs(report_folder, exist_ok=True)

    yield app

    # Final cleanup after test
    if os.path.exists(report_folder):
        shutil.rmtree(report_folder, ignore_errors=True)


def test_upload_and_results_page(app):
    client = app.test_client()
    data = {
        "broker": "tasty",
        "account_size_start": "10000",
        "net_liquidity_now": "11000",
        "buying_power_available_now": "5000",
    }
    data["csv"] = (io.BytesIO(make_csv_bytes()), "sample.csv")
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Audit Summary" in html
    assert "Verdict" in html
    assert "Account Growth" in html
    assert "Buying Power Utilized" in html
    assert "54.5%" in html # (11000 - 5000) / 11000


def test_rejects_large_upload(app):
    client = app.test_client()
    # Force a tiny max size to trigger 413
    app.config["MAX_CONTENT_LENGTH"] = 100
    big = b"A" * 1024  # 1 KB
    data = {
        "broker": "auto",
        "csv": (io.BytesIO(big), "big.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 413
    assert "Upload too large" in resp.get_data(as_text=True)


def test_theme_dropdown_present_on_upload(app):
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for theme switcher elements
    assert "data-bs-theme-value" in html
    assert "bd-theme" in html


def _csv_bytes_with_times(t1: datetime, t2: datetime):
    # Build a closed trade around provided datetimes (classic tasty format)
    content = (
        "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n"
        f"{t1.strftime('%Y-%m-%d %H:%M')},MSFT,1,Buy to Open,1.00,0.00,{(t2+timedelta(days=30)).date()},500,Put\n"
        f"{t2.strftime('%Y-%m-%d %H:%M')},MSFT,1,Sell to Close,1.10,0.00,{(t2+timedelta(days=30)).date()},500,Put\n"
    )
    return content.encode("utf-8")


def test_upload_with_preset_last_7_days(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=2)
    t2 = now - timedelta(days=1)
    data = {
        "broker": "tasty",
        "date_mode": "7d",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last7.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_preset_ytd(app):
    client = app.test_client()
    now = datetime.now()
    jan2 = datetime(now.year, 1, 2, 10, 0)
    jan3 = datetime(now.year, 1, 3, 10, 0)
    data = {
        "broker": "tasty",
        "date_mode": "ytd",
        "csv": (io.BytesIO(_csv_bytes_with_times(jan2, jan3)), "ytd.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Expect to see the badge with Jan 1 as start
    assert f"{now.year}-01-01" in html


def test_upload_with_preset_last_14_days(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=10)
    t2 = now - timedelta(days=5)
    data = {
        "broker": "tasty",
        "date_mode": "14d",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last14.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_preset_last_1_month(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=20)
    t2 = now - timedelta(days=18)
    data = {
        "broker": "tasty",
        "date_mode": "1m",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last1m.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_preset_last_6_months(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=150)
    t2 = now - timedelta(days=149)
    data = {
        "broker": "tasty",
        "date_mode": "6m",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last6m.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_preset_last_1_year(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=300)
    t2 = now - timedelta(days=299)
    data = {
        "broker": "tasty",
        "date_mode": "1y",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last1y.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_preset_last_2_years(app):
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=500)
    t2 = now - timedelta(days=499)
    data = {
        "broker": "tasty",
        "date_mode": "2y",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last2y.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html


def test_upload_with_all_mode_shows_no_badge(app):
    # When "All" is selected, no date badge should be shown
    client = app.test_client()
    now = datetime.now()
    t1 = now - timedelta(days=2)
    t2 = now - timedelta(days=1)
    data = {
        "broker": "tasty",
        "date_mode": "all",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "all.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" not in html


def test_upload_with_custom_date_range(app):
    client = app.test_client()
    # Build CSV with dates inside the custom range
    t1 = datetime(2025, 1, 10, 10, 0)
    t2 = datetime(2025, 1, 11, 10, 0)
    data = {
        "broker": "tasty",
        "date_mode": "range",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "custom.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Range:" in html
    assert "2025-01-01" in html and "2025-01-31" in html


def test_upload_defaults_all_mode_when_missing(app):
    # If the client sends no date_mode field at all, backend should treat it as 'all'
    client = app.test_client()
    # Build a simple closed trade
    now = datetime.now()
    t1 = now - timedelta(days=2)
    t2 = now - timedelta(days=1)
    data = {
        "broker": "tasty",
        # intentionally omit date_mode
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "no_date_mode.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # No badge should be shown when analyzing everything
    assert "Range:" not in html


def test_upload_with_custom_range_missing_dates_redirects(app):
    # Selecting custom range without both dates should redirect with a warning flash
    client = app.test_client()
    # CSV content doesn't matter because it should not be processed
    data = {
        "broker": "tasty",
        "date_mode": "range",
        # omit start_date and end_date on purpose
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Please select both start and end dates" in html

def test_upload_invalid_file_type(app):
    client = app.test_client()
    data = {
        "csv": (io.BytesIO(b"this is not a csv"), "test.txt"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Only .csv files are allowed" in html

def test_upload_no_file(app):
    client = app.test_client()
    data = {
        "csv": (io.BytesIO(b""), ""),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Please choose a CSV file" in html

def test_upload_invalid_account_size(app):
    client = app.test_client()
    data = {
        "account_size_start": "not-a-number",
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Account Size Start must be a number" in html

def test_analysis_error(app):
    client = app.test_client()
    # Create a CSV that will cause an error during analysis
    csv_content = "Header1,Header2\nValue1,Value2"
    data = {
        "csv": (io.BytesIO(csv_content.encode("utf-8")), "error.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Failed to analyze CSV" in html

def test_download_endpoints(app):
    client = app.test_client()
    # First, perform an analysis to get a valid token
    data = {
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    
    # Extract the token from the response
    import re
    match = re.search(r'/download/([a-f0-9]+)/', html)
    assert match
    token = match.group(1)

    # Test the report.xlsx download
    resp_report = client.get(f"/download/{token}/report.xlsx")
    assert resp_report.status_code == 200
    assert resp_report.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Test invalid token
    resp_invalid_token = client.get("/download/invalidtoken/report.xlsx")
    assert resp_invalid_token.status_code == 404

    # Test invalid kind
    resp_invalid_kind = client.get(f"/download/{token}/invalid.kind")
    assert resp_invalid_kind.status_code == 404

def test_download_nonexistent_file(app):
    client = app.test_client()
    # First, perform an analysis to get a valid token
    data = {
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    
    # Extract the token from the response
    import re
    match = re.search(r'/download/([a-f0-9]+)/', html)
    assert match
    token = match.group(1)

    # Test downloading a non-existent file kind
    resp_nonexistent = client.get(f"/download/{token}/nonexistent.file")
    assert resp_nonexistent.status_code == 404
