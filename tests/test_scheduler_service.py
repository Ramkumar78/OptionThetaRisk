import pytest
import threading
from unittest.mock import patch, MagicMock
from webapp.services.scheduler_service import run_master_scan, start_scheduler
from flask import Flask

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app

@patch('webapp.services.scheduler_service.screen_master_convergence')
@patch('webapp.services.scheduler_service.cache_screener_result')
def test_run_master_scan_success(mock_cache, mock_scan):
    mock_scan.return_value = [{"ticker": "AAPL"}]

    run_master_scan()

    mock_scan.assert_called_with(region="us", time_frame="1d")
    mock_cache.assert_called_with(("master", "us", "1d"), [{"ticker": "AAPL"}])

@patch('webapp.services.scheduler_service.screen_master_convergence')
@patch('webapp.services.scheduler_service.cache_screener_result')
def test_run_master_scan_failure(mock_cache, mock_scan):
    mock_scan.side_effect = Exception("API Error")

    # Should catch exception and log error, not raise
    run_master_scan()

    mock_cache.assert_not_called()

@patch('webapp.services.scheduler_service.threading.Thread')
@patch('webapp.services.scheduler_service.schedule')
def test_start_scheduler(mock_schedule, mock_thread, app):
    # Mock threading.Thread to capture targets
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance

    start_scheduler(app)

    # Should start 2 threads: initial_run and run_loop
    assert mock_thread.call_count == 2
    mock_thread_instance.start.assert_called()

    # Should schedule the job
    mock_schedule.every.return_value.minutes.do.assert_called()
