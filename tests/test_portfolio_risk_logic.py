import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from option_auditor.portfolio_risk import analyze_portfolio_risk

@pytest.fixture
def mock_market_data(mocker):
    return mocker.patch('option_auditor.portfolio_risk.get_cached_market_data')

@pytest.fixture
def mock_yf_ticker(mocker):
    return mocker.patch('option_auditor.portfolio_risk.yf.Ticker')

def test_analyze_portfolio_risk_input_validation():
    # Test empty list
    assert analyze_portfolio_risk([]) == {}

    # Test missing keys
    assert analyze_portfolio_risk([{'ticker': 'A'}]) == {"error": "Invalid input format. Must contain 'ticker' and 'value'."}

    # Test zero total value
    assert analyze_portfolio_risk([{'ticker': 'A', 'value': 0}, {'ticker': 'B', 'value': 0}]) == {"error": "Total portfolio value is zero."}

def test_concentration_risk(mock_market_data):
    # Mock data to return empty DataFrame as prices are not needed for concentration
    mock_market_data.return_value = pd.DataFrame()

    positions = [
        {'ticker': 'NVDA', 'value': 20000}, # 20%
        {'ticker': 'AAPL', 'value': 80000}  # 80%
    ]
    result = analyze_portfolio_risk(positions)
    warnings = result['concentration_warnings']

    # Both are > 15%
    assert len(warnings) == 2
    assert any("NVDA" in w for w in warnings)
    assert any("AAPL" in w for w in warnings)

    # Test only one > 15%
    positions = [
        {'ticker': 'NVDA', 'value': 1000}, # 1%
        {'ticker': 'AAPL', 'value': 99000} # 99%
    ]
    result = analyze_portfolio_risk(positions)
    warnings = result['concentration_warnings']
    assert len(warnings) == 1
    assert any("AAPL" in w for w in warnings)

def test_sector_risk_known(mock_market_data):
    mock_market_data.return_value = pd.DataFrame()
    # NVDA is Technology, JPM is Financials
    # SECTOR_COMPONENTS has XLK: [NVDA, ...], XLF: [JPM, ...]

    positions = [
        {'ticker': 'NVDA', 'value': 40000}, # 40% Tech
        {'ticker': 'JPM', 'value': 60000}   # 60% Financials
    ]
    result = analyze_portfolio_risk(positions)

    breakdown = result['sector_breakdown']
    # Technology and Financials
    sectors = {item['name']: item['value'] for item in breakdown}

    # Check breakdown values
    assert sectors.get('Technology') == 40.0
    assert sectors.get('Financials') == 60.0

    warnings = result['sector_warnings']
    # Both > 30%
    assert len(warnings) == 2
    assert any("Technology" in w for w in warnings)
    assert any("Financials" in w for w in warnings)

def test_sector_risk_unknown(mock_market_data, mock_yf_ticker):
    mock_market_data.return_value = pd.DataFrame()

    # Setup mock for yf.Ticker
    mock_instance_1 = MagicMock()
    mock_instance_1.info = {'sector': 'Technology'}

    def side_effect(ticker):
        if ticker == 'UNKNOWN1':
            return mock_instance_1
        elif ticker == 'UNKNOWN2':
            # Raise exception to trigger 'Unknown' fallback
            raise Exception("API Error")
        return MagicMock(info={})

    mock_yf_ticker.side_effect = side_effect

    positions = [
        {'ticker': 'UNKNOWN1', 'value': 5000},  # Should be mapped to Technology (via yf lookup)
        {'ticker': 'UNKNOWN2', 'value': 5000}   # Should be Unknown
    ]

    result = analyze_portfolio_risk(positions)
    breakdown = result['sector_breakdown']
    sectors = {item['name']: item['value'] for item in breakdown}

    assert sectors.get('Technology') == 50.0
    assert sectors.get('Unknown') == 50.0

    # Check that Unknown > 30% does NOT trigger warning
    # We need a case where Unknown is > 30%
    positions = [{'ticker': 'UNKNOWN2', 'value': 10000}]
    result = analyze_portfolio_risk(positions)
    # 100% in Unknown
    # Verify Unknown sector does not trigger "SECTOR OVERLOAD"
    assert len(result['sector_warnings']) == 0
    # But Technology > 30% triggers it
    positions = [{'ticker': 'UNKNOWN1', 'value': 10000}]
    result = analyze_portfolio_risk(positions)
    assert len(result['sector_warnings']) == 1
    assert "Technology" in result['sector_warnings'][0]

def test_correlation_risk_high(mock_market_data):
    # Generate 100 days of data
    dates = pd.date_range(start='2023-01-01', periods=100)
    # Using Sine wave to ensure variance
    t = np.linspace(0, 10, 100)
    price_series = 100 + 10 * np.sin(t)

    # Create DataFrame with two identical columns
    df = pd.DataFrame({'A': price_series, 'B': price_series}, index=dates)

    # Mock return
    mock_market_data.return_value = df

    positions = [{'ticker': 'A', 'value': 1000}, {'ticker': 'B', 'value': 1000}]
    result = analyze_portfolio_risk(positions)

    pairs = result['high_correlation_pairs']
    # Correlation should be 1.0
    assert len(pairs) == 1
    assert pairs[0]['verdict'] == "🔥 DUPLICATE RISK"
    assert pairs[0]['score'] > 0.99

    # Diversification score
    # Avg corr = 1.0
    # Score = (1 - 1) * 100 = 0
    assert result['diversification_score'] == 0.0

def test_correlation_risk_negative(mock_market_data):
    dates = pd.date_range(start='2023-01-01', periods=100)
    t = np.linspace(0, 10, 100)
    # A goes up/down, B goes opposite
    price_A = 100 + 10 * np.sin(t)
    price_B = 100 - 10 * np.sin(t)

    df = pd.DataFrame({'A': price_A, 'B': price_B}, index=dates)
    mock_market_data.return_value = df

    positions = [{'ticker': 'A', 'value': 1000}, {'ticker': 'B', 'value': 1000}]
    result = analyze_portfolio_risk(positions)

    pairs = result['high_correlation_pairs']
    # Correlation should be -1.0

    found_hedge = False
    for p in pairs:
        if "GOOD HEDGE" in p['verdict']:
            found_hedge = True
            assert p['score'] < -0.99

    assert found_hedge

    # Diversification score
    # Avg corr = -1.0
    # Score = (1 - (-1)) * 100 = 200
    # Note: Returns are not perfectly -1 correlated due to denominator (pct_change), so use tolerance
    assert result['diversification_score'] > 190.0

def test_diversification_score_single_asset(mock_market_data):
    dates = pd.date_range(start='2023-01-01', periods=100)
    price_series = 100 + 10 * np.linspace(0, 10, 100)
    df = pd.DataFrame({'A': price_series}, index=dates)
    mock_market_data.return_value = df

    positions = [{'ticker': 'A', 'value': 1000}]
    result = analyze_portfolio_risk(positions)

    assert result['diversification_score'] == 0.0

def test_zero_value_positions(mock_market_data, mock_yf_ticker):
    mock_market_data.return_value = pd.DataFrame()

    # Ensure they are unknown so they map to 'Unknown' sector
    mock_yf_ticker.side_effect = Exception("API Error")

    positions = [
        {'ticker': 'FAKE_TICKER_1', 'value': 1000},
        {'ticker': 'FAKE_TICKER_2', 'value': 0} # Zero value
    ]
    # Should not crash
    result = analyze_portfolio_risk(positions)

    # Check breakdown
    breakdown = result['sector_breakdown']
    sectors = {item['name']: item['value'] for item in breakdown}

    # FAKE_TICKER_1 (Unknown) -> 1000
    # FAKE_TICKER_2 (Unknown) -> 0
    # Total Unknown -> 100%
    assert sectors.get('Unknown') == 100.0

def test_multi_index_handling(mock_market_data):
    # Simulate MultiIndex (Ticker, OHLC) from yfinance group_by='ticker'
    dates = pd.date_range(start='2023-01-01', periods=10)

    # Create MultiIndex Columns: (Ticker, PriceType)
    # yfinance typically returns (PriceType, Ticker) for multi-tickers if group_by='column' (default)
    # or (Ticker, PriceType) if group_by='ticker'.
    # The code handles both or specific cases.
    # "if isinstance(price_data.columns, pd.MultiIndex): ... if 'Close' in price_data.columns.get_level_values(1): closes = price_data.xs('Close', level=1, axis=1)"
    # This implies Ticker is level 0, PriceType ('Close') is level 1.

    arrays = [['A', 'A', 'B', 'B'], ['Open', 'Close', 'Open', 'Close']]
    tuples = list(zip(*arrays))
    index = pd.MultiIndex.from_tuples(tuples, names=['Ticker', 'PriceType'])

    data = np.random.rand(10, 4)
    df = pd.DataFrame(data, index=dates, columns=index)

    mock_market_data.return_value = df

    positions = [{'ticker': 'A', 'value': 1000}, {'ticker': 'B', 'value': 1000}]

    # Should not crash and should produce correlation matrix
    result = analyze_portfolio_risk(positions)
    assert 'correlation_matrix' in result
    assert len(result['correlation_matrix']) > 0
