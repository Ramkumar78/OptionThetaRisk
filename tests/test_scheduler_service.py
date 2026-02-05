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
@patch('webapp.services.scheduler_service.time')
@patch('webapp.services.scheduler_service.run_master_scan')
def test_start_scheduler_initial_run(mock_run_scan, mock_time, mock_schedule, mock_thread, app):
    # Capture the thread target
    targets = []
    def side_effect(target=None, daemon=None):
        targets.append(target)
        return MagicMock()

    mock_thread.side_effect = side_effect

    start_scheduler(app)

    # We expect 2 threads: initial_run and run_loop
    # Note: Order depends on implementation.
    # In implementation:
    # 1. Thread(target=initial_run).start()
    # 2. Thread(target=run_loop).start()

    assert len(targets) == 2
    initial_run = targets[0]

    # Execute initial_run
    initial_run()

    # Verify it waited and ran scan with context
    mock_time.sleep.assert_called_with(10)
    mock_run_scan.assert_called_once()

@patch('webapp.services.scheduler_service.threading.Thread')
@patch('webapp.services.scheduler_service.schedule')
@patch('webapp.services.scheduler_service.time')
@patch('webapp.services.scheduler_service.run_master_scan')
def test_start_scheduler_run_loop(mock_run_scan, mock_time, mock_schedule, mock_thread, app):
    targets = []
    def side_effect(target=None, daemon=None):
        targets.append(target)
        return MagicMock()

    mock_thread.side_effect = side_effect

    start_scheduler(app)

    run_loop = targets[1]

    # Mock schedule.run_pending to raise an exception once then succeed
    mock_schedule.run_pending.side_effect = [Exception("Test Error"), None]

    # Break loop via time.sleep raising exception
    mock_time.sleep.side_effect = [None, InterruptedError("Stop Loop")]

    try:
        run_loop()
    except InterruptedError:
        pass

    # called twice: once after exception, once after success
    assert mock_schedule.run_pending.call_count == 2
    assert mock_time.sleep.call_count == 2

@patch('webapp.services.scheduler_service.threading.Thread')
@patch('webapp.services.scheduler_service.schedule')
@patch('webapp.services.scheduler_service.run_master_scan')
def test_schedule_registration(mock_run_scan, mock_schedule, mock_thread, app):
    start_scheduler(app)

    # Check that schedule.every(15).minutes.do(run_with_context) was called
    mock_schedule.every.assert_called_with(15)
    mock_schedule.every.return_value.minutes.do.assert_called()

    # Capture the registered job
    registered_job = mock_schedule.every.return_value.minutes.do.call_args[0][0]

    # Run the job
    registered_job()
    mock_run_scan.assert_called()
