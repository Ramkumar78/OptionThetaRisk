import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from option_auditor.portfolio_risk import analyze_portfolio_risk

@pytest.fixture
def mock_market_data():
    with patch('option_auditor.portfolio_risk.get_cached_market_data') as mock:
        yield mock

def test_concentration_warning(mock_market_data):
    """Test that a position > 15% triggers a concentration warning."""
    # Mock empty market data as we focus on concentration logic
    mock_market_data.return_value = pd.DataFrame()

    positions = [
        {'ticker': 'AAPL', 'value': 2000},
        {'ticker': 'MSFT', 'value': 8000}  # 80% of portfolio
    ]

    result = analyze_portfolio_risk(positions)

    assert "concentration_warnings" in result
    warnings = result["concentration_warnings"]
    assert len(warnings) > 0
    assert any("MSFT" in w and "HIGH CONCENTRATION" in w for w in warnings)

def test_sector_mapping_logic(mock_market_data):
    """Test sector mapping for known and unknown tickers."""
    mock_market_data.return_value = pd.DataFrame()

    # Mock Sector Constants
    mock_sector_components = {'TECH': ['KNOWN1']}
    mock_sector_names = {'TECH': 'Technology'}

    with patch('option_auditor.portfolio_risk.SECTOR_COMPONENTS', mock_sector_components), \
         patch('option_auditor.portfolio_risk.SECTOR_NAMES', mock_sector_names), \
         patch('yfinance.Ticker') as mock_ticker:

        # Mock yfinance for unknown ticker
        mock_instance = MagicMock()
        mock_instance.info = {'sector': 'Energy'}
        mock_ticker.return_value = mock_instance

        positions = [
            {'ticker': 'KNOWN1', 'value': 5000},
            {'ticker': 'UNKNOWN1', 'value': 5000}
        ]

        result = analyze_portfolio_risk(positions)

        sector_breakdown = result.get("sector_breakdown", [])

        # Check Technology Sector
        tech_sector = next((s for s in sector_breakdown if s['name'] == 'Technology'), None)
        assert tech_sector is not None
        assert tech_sector['value'] == 50.0

        # Check Energy Sector (via fallback)
        energy_sector = next((s for s in sector_breakdown if s['name'] == 'Energy'), None)
        assert energy_sector is not None
        assert energy_sector['value'] == 50.0

def test_sector_overload_warning(mock_market_data):
    """Test that a sector > 30% triggers a sector overload warning."""
    mock_market_data.return_value = pd.DataFrame()

    mock_sector_components = {'TECH': ['T1', 'T2']}
    mock_sector_names = {'TECH': 'Technology'}

    with patch('option_auditor.portfolio_risk.SECTOR_COMPONENTS', mock_sector_components), \
         patch('option_auditor.portfolio_risk.SECTOR_NAMES', mock_sector_names):

        positions = [
            {'ticker': 'T1', 'value': 4000},  # 40% Tech
            {'ticker': 'OTHER', 'value': 6000} # 60% Unknown/Other
        ]

        result = analyze_portfolio_risk(positions)

        warnings = result.get("sector_warnings", [])
        assert len(warnings) > 0
        assert any("Technology" in w and "SECTOR OVERLOAD" in w for w in warnings)

def test_correlation_matrix_math(mock_market_data):
    """Test correlation logic: Duplicate Risk, Good Hedge, and Diversification Score."""

    # Create controlled price data
    # A: Oscillating up
    # B: Identical to A (Corr = 1.0)
    # C: Mirror image (Corr = -1.0)
    dates = pd.date_range(start='2023-01-01', periods=6)
    data = {
        'A': [100, 102, 101, 103, 102, 104],
        'B': [100, 102, 101, 103, 102, 104],
        'C': [100, 98, 99, 97, 98, 96]
    }
    df = pd.DataFrame(data, index=dates)

    # analyze_portfolio_risk expects a DataFrame where columns are Tickers or MultiIndex
    # Logic in function: if 'Close' in columns -> single ticker. If simple DF -> assumes columns are tickers?
    # Let's look at the implementation:
    # "if len(ticker_list) == 1 ... else: closes = price_data"
    # So if we pass a DF with ticker columns, it uses it as closes.
    mock_market_data.return_value = df

    positions = [
        {'ticker': 'A', 'value': 1000},
        {'ticker': 'B', 'value': 1000},
        {'ticker': 'C', 'value': 1000}
    ]

    result = analyze_portfolio_risk(positions)

    high_corr_pairs = result.get("high_correlation_pairs", [])

    # Check for Duplicate Risk (A + B)
    dup_risk = next((p for p in high_corr_pairs if 'A + B' in p['pair'] or 'B + A' in p['pair']), None)
    assert dup_risk is not None
    assert dup_risk['verdict'] == "🔥 DUPLICATE RISK"
    assert dup_risk['score'] >= 0.99

    # Check for Good Hedge (A + C)
    hedge = next((p for p in high_corr_pairs if 'A + C' in p['pair'] or 'C + A' in p['pair']), None)
    assert hedge is not None
    assert hedge['verdict'] == "✅ GOOD HEDGE"
    assert hedge['score'] <= -0.99

    # Diversification Score
    # Avg Corr calculation:
    # Matrix:
    #    A    B    C
    # A  1.0  1.0 -1.0
    # B  1.0  1.0 -1.0
    # C -1.0 -1.0  1.0
    # Sum = 1+1-1 + 1+1-1 + -1-1+1 = 1 + 1 - 1 = 1.0
    # n = 3. Sum = 1.0.
    # avg_corr = (1.0 - 3) / (9 - 3) = -2 / 6 = -0.333
    # div_score = (1 - (-0.333)) * 100 = 1.333 * 100 = 133.3 ??
    # Wait, div_score logic: div_score = (1 - avg_corr) * 100
    # If perfect negative correlation, diversification is > 100? Let's check logic.
    # Usually diversification score is 0-100.
    # But formula: (1 - avg_corr) * 100. Range of avg_corr is -1 to 1.
    # If avg_corr is -1, score is 200. If 1, score is 0.
    # The function implements it this way. So we expect ~133.3.

    div_score = result.get("diversification_score")
    # 133.3 is expected given the formula and data
    assert div_score > 100.0
