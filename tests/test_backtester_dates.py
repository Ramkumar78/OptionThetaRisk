import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from option_auditor.unified_backtester import UnifiedBacktester
from webapp.app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_unified_backtester_custom_dates():
    # Test logic after fetch_data by mocking fetch_data
    with patch.object(UnifiedBacktester, 'fetch_data') as mock_fetch:
        dates = pd.date_range(start='2015-01-01', end='2025-01-01', freq='B') # Business days
        data = pd.DataFrame({
            'Close': 100.0, 'High': 105.0, 'Low': 95.0, 'Open': 100.0, 'Volume': 1000000,
            'Spy': 300.0, 'Vix': 20.0
        }, index=dates)
        # Add some trend to make it valid for indicators
        data['Close'] = data['Close'] + range(len(data))
        data['High'] = data['Close'] + 5
        data['Low'] = data['Close'] - 5

        mock_fetch.return_value = data

        # 1. Test Custom Date Range (e.g. 2020-01-01 to 2021-01-01)
        ub = UnifiedBacktester("TEST", start_date="2020-01-01", end_date="2021-01-01")
        res = ub.run()

        assert "error" not in res, res
        assert res['start_date'] == '2020-01-01'
        # The end date might be the last available trading day <= 2021-01-01
        assert res['end_date'] <= '2021-01-01'
        assert res['end_date'] >= '2020-12-31' # Should be close (Jan 1 is holiday usually, but freq='B' includes it if weekday?)

        # Verify equity curve length corresponds roughly to 1 year (~260 trading days) minus warmup
        # UnifiedBacktester skips 20 warmup days.
        # B days in 2020: 262.
        assert 200 < len(res['equity_curve']) < 270

def test_unified_backtester_default_dates():
     with patch.object(UnifiedBacktester, 'fetch_data') as mock_fetch:
        dates = pd.date_range(start='2015-01-01', end=pd.Timestamp.now(), freq='B')
        data = pd.DataFrame({
            'Close': 100.0, 'High': 105.0, 'Low': 95.0, 'Open': 100.0, 'Volume': 1000000,
            'Spy': 300.0, 'Vix': 20.0
        }, index=dates)
        data['Close'] = data['Close'] + range(len(data))
        data['High'] = data['Close'] + 5
        data['Low'] = data['Close'] - 5
        mock_fetch.return_value = data

        ub = UnifiedBacktester("TEST")
        res = ub.run()

        # Default is 5 years.
        # Check start date is approx 5 years ago.
        start_date = pd.Timestamp(res['start_date'])
        target = pd.Timestamp.now() - pd.Timedelta(days=1825)

        # Allow some margin because of 'B' freq and data availability
        diff = abs((start_date - target).days)
        assert diff < 10 # Should be very close

def test_api_backtest_custom_dates(client):
    with patch('webapp.blueprints.analysis_routes.UnifiedBacktester') as mock_ub_cls:
        instance = mock_ub_cls.return_value
        instance.run.return_value = {"ticker": "AAPL", "start_date": "2020-01-01", "end_date": "2021-01-01"}

        payload = {
            "ticker": "AAPL",
            "strategy": "master",
            "initial_capital": 10000,
            "start_date": "2020-01-01",
            "end_date": "2021-01-01"
        }

        resp = client.post("/analyze/backtest", json=payload)
        assert resp.status_code == 200

        mock_ub_cls.assert_called_with(
            "AAPL",
            strategy_type="master",
            initial_capital=10000.0,
            start_date="2020-01-01",
            end_date="2021-01-01"
        )
