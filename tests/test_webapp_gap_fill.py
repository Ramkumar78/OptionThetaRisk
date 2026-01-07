import pytest
import json
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import io
import time
from flask import session
import pandas as pd

@pytest.fixture
def client_with_mock_storage():
    # Use patch to mock get_storage_provider before creating app
    # to avoid issues with database initialization in create_app
    with patch("webapp.app.get_storage_provider") as mock_storage:
        from webapp.app import create_app
        app = create_app(testing=True)
        app.secret_key = "test"
        mock_provider = MagicMock()
        # Configure methods to return JSON-serializable values
        mock_provider.save_journal_entry.return_value = "mock_id"

        mock_storage.return_value = mock_provider

        with app.test_client() as client:
            yield client, mock_provider

def test_cache_logic():
    from webapp.app import get_cached_screener_result, cache_screener_result, screener_cache

    key = "test_key"
    data = {"foo": "bar"}

    # Test Cache Miss
    screener_cache.cache.clear()
    assert get_cached_screener_result(key) is None

    # Test Cache Hit
    cache_screener_result(key, data)
    assert get_cached_screener_result(key) == data

    # Test Cache Expiry
    screener_cache.cache[key] = (data, time.time() - screener_cache.ttl - 1)
    assert get_cached_screener_result(key) is None

def test_send_email_notification_missing_key():
    from webapp.app import send_email_notification
    with patch("webapp.app._get_env_or_docker_default", return_value=None):
        with patch("builtins.print") as mock_print:
            send_email_notification("Subj", "Body")
            mock_print.assert_any_call("⚠️  Resend API Key missing. Skipping email.", flush=True)

def test_send_email_notification_success():
    from webapp.app import send_email_notification
    with patch("webapp.app._get_env_or_docker_default", return_value="key"):
        with patch("resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "123"}
            send_email_notification("Subj", "Body")
            mock_send.assert_called_once()

def test_send_email_notification_failure():
    from webapp.app import send_email_notification
    with patch("webapp.app._get_env_or_docker_default", return_value="key"):
        with patch("resend.Emails.send", side_effect=Exception("Fail")):
            with patch("builtins.print") as mock_print:
                send_email_notification("Subj", "Body")
                assert any("Failed to send email" in str(call) for call in mock_print.call_args_list)

def test_cleanup_job():
    from webapp.app import cleanup_job, CLEANUP_INTERVAL
    app = MagicMock()
    app.app_context.return_value.__enter__.return_value = None

    mock_storage = MagicMock()
    with patch("webapp.app._get_storage_provider", return_value=mock_storage):
        with patch("time.sleep", side_effect=InterruptedError):
            try:
                cleanup_job(app)
            except InterruptedError:
                pass
            mock_storage.cleanup_old_reports.assert_called()

def test_feedback_route_empty(client_with_mock_storage):
    client, _ = client_with_mock_storage
    res = client.post("/feedback", data={"message": ""})
    assert res.status_code == 400
    assert "Message cannot be empty" in res.json["error"]

def test_feedback_route_success(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage
    with patch("threading.Thread") as mock_thread:
        res = client.post("/feedback", data={"message": "Great app!", "name": "User", "email": "u@e.com"})
        assert res.status_code == 200
        mock_storage.save_feedback.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

def test_feedback_route_failure(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage
    mock_storage.save_feedback.side_effect = Exception("DB Error")
    res = client.post("/feedback", data={"message": "msg"})
    assert res.status_code == 500

def test_dashboard_no_portfolio(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage
    mock_storage.get_portfolio.return_value = None
    res = client.get("/dashboard")
    assert res.json["error"] == "No portfolio found"

def test_dashboard_success(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage
    mock_storage.get_portfolio.return_value = json.dumps({"foo": "bar"}).encode('utf-8')
    with patch("webapp.app.refresh_dashboard_data", return_value={"foo": "bar", "refreshed": True}):
        res = client.get("/dashboard")
        assert res.json["refreshed"] is True

def test_health(client_with_mock_storage):
    client, _ = client_with_mock_storage
    res = client.get("/health")
    assert res.status_code == 200

def test_screen_params(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_market", return_value=[]):
        with patch("webapp.app.screener.screen_sectors", return_value=[]):
            res = client.post("/screen", data={"iv_rank": "invalid", "rsi_threshold": "60"})
            assert res.status_code == 200
            assert res.json["params"]["iv_rank"] == 30.0
            assert res.json["params"]["rsi"] == 60.0

def test_screen_error(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_market", side_effect=Exception("Screener fail")):
        res = client.post("/screen", data={})
        assert res.status_code == 500

# FIXED: Test Turtle region via get_cached_market_data mock
def test_screen_turtle_regions(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.get_cached_market_data") as mock_data:
        mock_data.return_value = pd.DataFrame() # Empty return
        client.get("/screen/turtle?region=sp500")

        # Verify call args
        args, _ = mock_data.call_args
        # First arg is ticker list. SP500 should be > 400 items.
        assert len(args[0]) > 100

# FIXED: Test ISA error handling (returns 200 with empty list on loop error)
def test_screen_isa_error(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.IsaStrategy") as MockStrat:
        instance = MockStrat.return_value
        instance.analyze.side_effect = Exception("Fail")

        with patch("webapp.app.get_cached_market_data") as mock_data:
            mock_data.return_value = pd.DataFrame({"Close": [100]}, index=[0]) # Dummy data
            res = client.get("/screen/isa")
            assert res.status_code == 200
            assert res.json == {"results": []}

def test_check_isa_stock_missing(client_with_mock_storage):
    client, _ = client_with_mock_storage
    res = client.get("/screen/isa/check")
    assert res.status_code == 400

def test_check_isa_stock_not_found(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.resolve_ticker", return_value="BAD"):
        with patch("webapp.app.screener.screen_trend_followers_isa", return_value=[]):
            res = client.get("/screen/isa/check?ticker=BAD")
            assert res.status_code == 404

def test_check_isa_stock_with_entry(client_with_mock_storage):
    client, _ = client_with_mock_storage
    fake_result = {
        "ticker": "AAPL", "price": 150, "signal": "ENTER", "trailing_exit_20d": 140
    }
    with patch("webapp.app.screener.resolve_ticker", return_value="AAPL"):
        with patch("webapp.app.screener.screen_trend_followers_isa", return_value=[fake_result]):
            res = client.get("/screen/isa/check?ticker=AAPL&entry_price=130")
            assert res.json["pnl_value"] == 20
            assert "HOLD" in res.json["signal"]

def test_screen_bull_put_regions(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_bull_put_spreads", return_value=[]) as mock_screen:
        with patch("webapp.app.screener._get_filtered_sp500", return_value=["SPY"]):
             client.get("/screen/bull_put?region=sp500")
             mock_screen.assert_called()

def test_screen_darvas_error(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_darvas_box", side_effect=Exception("Fail")):
        res = client.get("/screen/darvas")
        assert res.status_code == 500

def test_screen_ema_regions(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_5_13_setups", return_value=[]):
        res = client.get("/screen/ema?region=india")
        assert res.status_code == 200

def test_screen_mms_regions(client_with_mock_storage):
    client, _ = client_with_mock_storage
    with patch("webapp.app.screener.screen_mms_ote_setups", return_value=[]):
         res = client.get("/screen/mms?region=sp500")
         assert res.status_code == 200

def test_journal_routes(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage

    res = client.post("/journal/add", json={"symbol": "AAPL"})
    assert res.status_code == 200
    mock_storage.save_journal_entry.assert_called()

    res = client.delete("/journal/delete/123")
    assert res.status_code == 200
    mock_storage.delete_journal_entry.assert_called()

    with patch("webapp.app.journal_analyzer.analyze_journal", return_value={}):
        res = client.post("/journal/analyze", json={})
        assert res.status_code == 200

def test_journal_import_trades(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage
    mock_storage.save_journal_entries.return_value = 1

    res = client.post("/journal/import", json={})
    assert res.status_code == 400

    trades = [
        {"symbol": "AAPL", "pnl": 100, "segments": [{"entry_ts": "2023-01-01T10:00:00"}]}
    ]
    res = client.post("/journal/import", json=trades)
    assert res.status_code == 200
    mock_storage.save_journal_entries.assert_called()

def test_analyze_route(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage

    res = client.post("/analyze")
    assert res.status_code == 400

    data = {"csv": (io.BytesIO(b"content"), "file.txt")}
    res = client.post("/analyze", data=data)
    assert res.status_code == 400

    with patch("webapp.app.analyze_csv") as mock_analyze:
        mock_analyze.return_value = {"excel_report": io.BytesIO(b"xlsx"), "results": []}
        data = {"csv": (io.BytesIO(b"content"), "file.csv")}
        res = client.post("/analyze", data=data)
        assert res.status_code == 200
        assert "token" in res.json
        mock_storage.save_report.assert_called()
        mock_storage.save_portfolio.assert_called()

    with patch("webapp.app.analyze_csv", side_effect=Exception("Fail")):
        data = {"csv": (io.BytesIO(b"content"), "file.csv")}
        res = client.post("/analyze", data=data)
        assert res.status_code == 500

def test_download_route(client_with_mock_storage):
    client, mock_storage = client_with_mock_storage

    mock_storage.get_report.return_value = b"file content"
    res = client.get("/download/token/file.xlsx")
    assert res.status_code == 200

    mock_storage.get_report.return_value = None
    res = client.get("/download/token/missing.xlsx")
    assert res.status_code == 404

def test_catch_all(client_with_mock_storage):
    client, _ = client_with_mock_storage

    res = client.get("/api/foo")
    assert res.status_code == 404

    with patch("os.path.exists", return_value=False):
         res = client.get("/some/page")
