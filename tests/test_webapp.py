import io
from datetime import datetime, timedelta
import pytest

def make_csv_bytes():
    content = (
        "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n"
        "2025-01-01 10:00,MSFT,1,Buy to Open,1.00,0.10,2025-02-21,500,Put\n"
        "2025-01-03 10:00,MSFT,1,Sell to Close,1.50,0.10,2025-02-21,500,Put\n"
    )
    return content.encode("utf-8")

def test_upload_and_results_page(authed_client):
    data = {
        "broker": "tasty",
        "account_size_start": "10000",
        "net_liquidity_now": "11000",
        "buying_power_available_now": "5000",
    }
    data["csv"] = (io.BytesIO(make_csv_bytes()), "sample.csv")
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Net PnL" in html
    assert "Strategy Performance" in html
    assert "Verdict" in html
    assert "BP Usage" in html
    assert "55%" in html

def test_rejects_large_upload(app, authed_client):
    app.config["MAX_CONTENT_LENGTH"] = 100
    big = b"A" * 1024
    data = {
        "broker": "auto",
        "csv": (io.BytesIO(big), "big.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 413
    assert "Upload too large" in resp.get_data(as_text=True)

def _csv_bytes_with_times(t1: datetime, t2: datetime):
    content = (
        "Time,Underlying Symbol,Quantity,Action,Price,Commissions and Fees,Expiration Date,Strike Price,Option Type\n"
        f"{t1.strftime('%Y-%m-%d %H:%M')},MSFT,1,Buy to Open,1.00,0.00,{(t2+timedelta(days=30)).date()},500,Put\n"
        f"{t2.strftime('%Y-%m-%d %H:%M')},MSFT,1,Sell to Close,1.10,0.00,{(t2+timedelta(days=30)).date()},500,Put\n"
    )
    return content.encode("utf-8")

def test_upload_with_preset_last_7_days(authed_client):
    now = datetime.now()
    t1 = now - timedelta(days=2)
    t2 = now - timedelta(days=1)
    data = {
        "broker": "tasty",
        "date_mode": "7d",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "last7.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Analysis Period" in html

def test_upload_with_preset_ytd(authed_client):
    now = datetime.now()
    jan2 = datetime(now.year, 1, 2, 10, 0)
    jan3 = datetime(now.year, 1, 3, 10, 0)
    data = {
        "broker": "tasty",
        "date_mode": "ytd",
        "csv": (io.BytesIO(_csv_bytes_with_times(jan2, jan3)), "ytd.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert f"{now.year}-01-01" in html

def test_upload_with_all_mode_shows_no_badge(authed_client):
    now = datetime.now()
    t1 = now - timedelta(days=2)
    t2 = now - timedelta(days=1)
    data = {
        "broker": "tasty",
        "date_mode": "all",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "all.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Analysis Period" not in html

def test_upload_with_custom_date_range(authed_client):
    t1 = datetime(2025, 1, 10, 10, 0)
    t2 = datetime(2025, 1, 11, 10, 0)
    data = {
        "broker": "tasty",
        "date_mode": "range",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "csv": (io.BytesIO(_csv_bytes_with_times(t1, t2)), "custom.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Analysis Period" in html
    assert "2025-01-01" in html and "2025-01-31" in html

def test_upload_with_custom_range_missing_dates_redirects(authed_client):
    data = {
        "broker": "tasty",
        "date_mode": "range",
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Please select both start and end dates" in html

def test_upload_invalid_file_type(authed_client):
    data = {
        "csv": (io.BytesIO(b"this is not a csv"), "test.txt"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Only .csv files are allowed" in html

def test_upload_no_file(authed_client):
    data = {
        "csv": (io.BytesIO(b""), ""),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Please choose a CSV file or enter trades manually" in html

def test_upload_invalid_account_size(authed_client):
    data = {
        "account_size_start": "not-a-number",
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Account Size Start must be a number" in html

def test_analysis_error(authed_client):
    csv_content = "Header1,Header2\nValue1,Value2"
    data = {
        "csv": (io.BytesIO(csv_content.encode("utf-8")), "error.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Failed to analyze" in html

def test_download_endpoints(authed_client):
    data = {
        "csv": (io.BytesIO(make_csv_bytes()), "sample.csv"),
    }
    resp = authed_client.post("/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    
    import re
    match = re.search(r'/download/([a-f0-9]+)/', html)
    assert match
    token = match.group(1)

    resp_report = authed_client.get(f"/download/{token}/report.xlsx")
    assert resp_report.status_code == 200
    assert resp_report.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    resp_invalid_token = authed_client.get("/download/invalidtoken/report.xlsx")
    assert resp_invalid_token.status_code == 404

    resp_invalid_kind = authed_client.get(f"/download/{token}/invalid.kind")
    assert resp_invalid_kind.status_code == 404

def test_homepage_links(authed_client):
    resp = authed_client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "https://github.com/Ramkumar78/OptionThetaRisk" in html
    assert "GitHub" in html
