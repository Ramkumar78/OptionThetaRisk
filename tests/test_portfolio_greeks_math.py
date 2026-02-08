import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime
from option_auditor import portfolio_risk

# Fixture for market data
@pytest.fixture
def mock_market_data():
    dates = pd.date_range(start='2024-01-01', periods=100)
    data = {
        'AAPL': np.linspace(150, 160, 100),
        'GOOG': np.linspace(2800, 2900, 100)
    }
    return pd.DataFrame(data, index=dates)

# Test Aggregation
def test_analyze_portfolio_greeks_aggregation(mock_market_data):
    with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock_get_data, \
         patch('option_auditor.portfolio_risk.calculate_greeks') as mock_calc_greeks, \
         patch('option_auditor.portfolio_risk.datetime') as mock_datetime:

        mock_get_data.return_value = mock_market_data

        # Mock datetime.now()
        fixed_now = datetime(2024, 6, 1, 10, 0, 0)
        mock_datetime.now.return_value = fixed_now
        # Mock strptime to use real implementation
        mock_datetime.strptime.side_effect = lambda d, f: datetime.strptime(d, f)

        # Mock calculate_greeks to return fixed values
        mock_calc_greeks.return_value = {
            "delta": 0.5, "gamma": 0.1, "theta": -0.05, "vega": 0.2, "rho": 0.01
        }

        positions = [
            {'ticker': 'AAPL', 'type': 'call', 'strike': 160, 'expiry': '2024-06-30', 'qty': 1},
            {'ticker': 'GOOG', 'type': 'put', 'strike': 2800, 'expiry': '2024-06-30', 'qty': 2}
        ]

        result = portfolio_risk.analyze_portfolio_greeks(positions)

        totals = result['portfolio_totals']

        # Expected Delta:
        # Pos 1: 0.5 * 100 * 1 = 50
        # Pos 2: 0.5 * 100 * 2 = 100
        # Total: 150
        assert totals['delta'] == 150.0

        # Expected Gamma:
        # Pos 1: 0.1 * 100 * 1 = 10
        # Pos 2: 0.1 * 100 * 2 = 20
        # Total: 30
        assert totals['gamma'] == 30.0

# Test Expired Options
def test_analyze_portfolio_greeks_expired(mock_market_data):
    with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock_get_data, \
         patch('option_auditor.portfolio_risk.calculate_greeks') as mock_calc_greeks, \
         patch('option_auditor.portfolio_risk.datetime') as mock_datetime:

        mock_get_data.return_value = mock_market_data

        fixed_now = datetime(2024, 6, 1, 10, 0, 0)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime.side_effect = lambda d, f: datetime.strptime(d, f)

        mock_calc_greeks.return_value = {
            "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0
        }

        # Expiry in past relative to fixed_now (2024-06-01)
        positions = [
            {'ticker': 'AAPL', 'type': 'call', 'strike': 160, 'expiry': '2024-05-01', 'qty': 1}
        ]

        portfolio_risk.analyze_portfolio_greeks(positions)

        # Verify calculate_greeks called with T=0
        # call_args is (args, kwargs)
        args, _ = mock_calc_greeks.call_args
        # args: (S, strike, T, r, sigma, otype)
        # S is from mock data (approx 160 for AAPL), strike=160, T=?, r=0.045, sigma=?, otype='call'
        assert args[2] == 0

# Test Multiplier
def test_analyze_portfolio_greeks_multiplier(mock_market_data):
    with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock_get_data, \
         patch('option_auditor.portfolio_risk.calculate_greeks') as mock_calc_greeks, \
         patch('option_auditor.portfolio_risk.datetime') as mock_datetime:

        mock_get_data.return_value = mock_market_data

        fixed_now = datetime(2024, 6, 1, 10, 0, 0)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime.side_effect = lambda d, f: datetime.strptime(d, f)

        mock_calc_greeks.return_value = {
            "delta": 1.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0
        }

        positions = [
            {'ticker': 'AAPL', 'type': 'call', 'strike': 160, 'expiry': '2024-06-30', 'qty': 1.5}
        ]

        result = portfolio_risk.analyze_portfolio_greeks(positions)
        totals = result['portfolio_totals']

        # Expected Delta: 1.0 * 100 * 1.5 = 150
        assert totals['delta'] == 150.0

# Test Robustness (Missing Data)
def test_analyze_portfolio_greeks_robustness(mock_market_data):
    with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock_get_data, \
         patch('option_auditor.portfolio_risk.calculate_greeks') as mock_calc_greeks, \
         patch('option_auditor.portfolio_risk.datetime') as mock_datetime:

        # Mock data only has AAPL, missing MSFT
        mock_get_data.return_value = mock_market_data[['AAPL']]

        fixed_now = datetime(2024, 6, 1, 10, 0, 0)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime.side_effect = lambda d, f: datetime.strptime(d, f)

        mock_calc_greeks.return_value = {
            "delta": 0.5, "gamma": 0.1, "theta": -0.05, "vega": 0.2, "rho": 0.01
        }

        positions = [
            {'ticker': 'AAPL', 'type': 'call', 'strike': 160, 'expiry': '2024-06-30', 'qty': 1},
            {'ticker': 'MSFT', 'type': 'put', 'strike': 300, 'expiry': '2024-06-30', 'qty': 1}
        ]

        result = portfolio_risk.analyze_portfolio_greeks(positions)

        # MSFT should be in positions but marked as error or skipped from totals
        positions_out = result['positions']

        aapl_pos = next((p for p in positions_out if p['ticker'] == 'AAPL'), None)
        msft_pos = next((p for p in positions_out if p['ticker'] == 'MSFT'), None)

        assert aapl_pos is not None
        assert msft_pos is not None
        assert 'error' in msft_pos
        assert msft_pos['error'] == 'Price unavailable'

        # Totals should only reflect AAPL
        totals = result['portfolio_totals']
        # AAPL delta: 0.5 * 100 * 1 = 50.0
        assert totals['delta'] == 50.0
