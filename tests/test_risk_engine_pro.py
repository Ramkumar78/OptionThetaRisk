import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.risk_engine_pro import RiskEngine
from option_auditor.models import TradeGroup

@pytest.fixture
def mock_market_data():
    # Create a MultiIndex DataFrame to simulate yfinance download result
    dates = pd.date_range(end=datetime.now(), periods=50, freq='B')
    N = len(dates)

    # Ticker 1: AAPL
    df1 = pd.DataFrame({'Close': np.linspace(150, 160, N)}, index=dates)

    # Ticker 2: TSLA
    df2 = pd.DataFrame({'Close': np.linspace(200, 220, N)}, index=dates)

    # Combine into MultiIndex: (Price, Ticker) or (Ticker, Price) - usually (Price, Ticker)
    # yfinance typically returns MultiIndex columns: (Adjs Close, AAPL), (Close, AAPL), etc.
    # Let's mock the structure used in data_utils or what RiskEngine expects
    # RiskEngine expects:
    # if MultiIndex: data[ticker]['Close'] or data.xs('Close', level=0)[ticker]

    # Let's create a structure: columns = MultiIndex.from_product([['AAPL', 'TSLA'], ['Close']])
    cols = pd.MultiIndex.from_product([['AAPL', 'TSLA'], ['Close']])
    data = pd.DataFrame(index=dates, columns=cols)
    data[('AAPL', 'Close')] = df1['Close']
    data[('TSLA', 'Close')] = df2['Close']

    return data

def test_init_mixed_inputs():
    # 1. Dictionary Input
    pos1 = {
        'symbol': 'AAPL',
        'qty': 10,
        'value': 1500
    }

    # 2. TradeGroup Input
    pos2 = TradeGroup(
        contract_id='123',
        symbol='TSLA',
        expiry=None,
        strike=None,
        right=None,
        qty_net=5
    )

    # 3. Option Dict Input
    pos3 = {
        'ticker': 'NVDA',
        'type': 'call',
        'strike': 500,
        'expiry': '2023-12-15',
        'qty': 1
    }

    engine = RiskEngine([pos1, pos2, pos3])

    assert len(engine.positions) == 3

    # Verify AAPL
    p1 = next(p for p in engine.positions if p['symbol'] == 'AAPL')
    assert p1['qty'] == 10
    assert p1['multiplier'] == 1.0 # Stock

    # Verify TSLA
    p2 = next(p for p in engine.positions if p['symbol'] == 'TSLA')
    assert p2['qty'] == 5
    assert p2['multiplier'] == 1.0

    # Verify NVDA
    p3 = next(p for p in engine.positions if p['symbol'] == 'NVDA')
    assert p3['qty'] == 1
    assert p3['multiplier'] == 100.0
    assert p3['right'] == 'C'
    assert p3['strike'] == 500.0

@patch('option_auditor.risk_engine_pro.get_cached_market_data')
def test_fetch_market_data(mock_get_data, mock_market_data):
    mock_get_data.return_value = mock_market_data

    positions = [{'symbol': 'AAPL', 'qty': 10}, {'symbol': 'TSLA', 'qty': 5}]
    engine = RiskEngine(positions)

    # Trigger fetch
    engine._fetch_market_data()

    assert 'AAPL' in engine.market_data
    assert 'TSLA' in engine.market_data

    aapl = engine.market_data['AAPL']
    assert aapl['price'] == 160.0 # Last value in linspace(150, 160, 50)
    assert aapl['vol'] > 0 # Volatility should be calculated

    tsla = engine.market_data['TSLA']
    assert tsla['price'] == 220.0

@patch('option_auditor.risk_engine_pro.get_cached_market_data')
def test_what_if_analysis(mock_get_data, mock_market_data):
    mock_get_data.return_value = mock_market_data

    # Setup: 10 shares of AAPL at 150 (current price ~160 in mock)
    # And 1 Long Call on TSLA (current ~220), Strike 220 (ATM), Expiry in future
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    positions = [
        {'symbol': 'AAPL', 'qty': 10},
        {'symbol': 'TSLA', 'qty': 1, 'type': 'call', 'strike': 220, 'expiry': future_date}
    ]

    engine = RiskEngine(positions)
    # Ensure market data is populated
    engine._fetch_market_data()
    # Mock specific prices for deterministic calc
    engine.market_data['AAPL'] = {'price': 100.0, 'vol': 0.2}
    engine.market_data['TSLA'] = {'price': 200.0, 'vol': 0.4}

    results = engine.run_what_if_analysis()

    assert len(results) == 21 # -10 to +10

    # Check 0% move
    zero_res = next(r for r in results if r.market_move_pct == 0.0)
    assert abs(zero_res.portfolio_value_change) < 1.0 # Should be 0, allowing float noise

    # Check +10% move
    # AAPL: 100 -> 110. Gain = 10 * 10 = 100.
    # TSLA: 200 -> 220. Call Value increases.
    plus_10 = next(r for r in results if r.market_move_pct == 10.0)
    assert plus_10.portfolio_value_change > 100.0 # At least the stock gain + option gain

    # Check -10% move
    # AAPL: 100 -> 90. Loss = -100.
    # TSLA: 200 -> 180. Call Value decreases.
    minus_10 = next(r for r in results if r.market_move_pct == -10.0)
    assert minus_10.portfolio_value_change < -100.0 # Stock loss + option loss

@patch('option_auditor.risk_engine_pro.get_cached_market_data')
def test_portfolio_greeks(mock_get_data, mock_market_data):
    mock_get_data.return_value = mock_market_data

    future_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

    # 100 Shares of AAPL. Delta = 100.
    # 1 Long Call ATM on TSLA. Delta approx 0.5 * 100 = 50.
    positions = [
        {'symbol': 'AAPL', 'qty': 100},
        {'symbol': 'TSLA', 'qty': 1, 'type': 'call', 'strike': 200, 'expiry': future_date}
    ]

    engine = RiskEngine(positions)
    engine._fetch_market_data()
    engine.market_data['AAPL'] = {'price': 100.0, 'vol': 0.2}
    engine.market_data['TSLA'] = {'price': 200.0, 'vol': 0.2}

    greeks = engine.calculate_portfolio_greeks()

    # Delta should be around 100 + 50 = 150
    assert 140 < greeks['delta'] < 160

    # Gamma should be positive (Long Call)
    assert greeks['gamma'] > 0

    # Theta should be negative (Long Call time decay)
    assert greeks['theta'] < 0

    # Vega should be positive (Long Call vol exposure)
    assert greeks['vega'] > 0

@patch('option_auditor.risk_engine_pro.portfolio_risk.analyze_portfolio_risk')
def test_correlation_heatmap(mock_analyze, mock_market_data):
    # Setup mock return
    mock_matrix = {
        'AAPL': {'AAPL': 1.0, 'TSLA': 0.5},
        'TSLA': {'AAPL': 0.5, 'TSLA': 1.0}
    }
    mock_analyze.return_value = {'correlation_matrix': mock_matrix}

    engine = RiskEngine([{'symbol': 'AAPL', 'qty': 10}, {'symbol': 'TSLA', 'qty': 10}])

    matrix = engine.generate_correlation_heatmap()

    assert matrix == mock_matrix
    mock_analyze.assert_called_once()
