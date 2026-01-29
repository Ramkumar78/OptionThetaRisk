import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from option_auditor.strategies.fourier import FourierStrategy
from option_auditor.screener import screen_fourier_cycles
from option_auditor.strategies.math_utils import calculate_hilbert_phase

class TestFourierStrategyClass:

    @patch('option_auditor.strategies.fourier.calculate_dominant_cycle')
    @patch('option_auditor.strategies.fourier.calculate_hilbert_phase')
    def test_fourier_cycle_bottom_patched(self, mock_phase, mock_cycle, mock_market_data):
         # Mock returns: Phase (pi or -pi -> bottom), Strength/Amplitude
         # FourierStrategy logic: 0.8 <= abs(phase/pi) <= 1.0 -> LOW
         mock_phase.return_value = (np.pi, 0.5)
         mock_cycle.return_value = (20.0, 0.0)

         df = mock_market_data(days=100)
         strategy = FourierStrategy("TEST", df)

         result = strategy.analyze()
         assert result is not None
         assert "LOW" in result['signal']
         assert result['cycle_phase'] == f"{np.pi:.2f} rad"

    @patch('option_auditor.strategies.fourier.calculate_dominant_cycle')
    @patch('option_auditor.strategies.fourier.calculate_hilbert_phase')
    def test_fourier_cycle_top_patched(self, mock_phase, mock_cycle, mock_market_data):
         # FourierStrategy logic: 0.0 <= abs(phase/pi) <= 0.2 -> HIGH
         mock_phase.return_value = (0.05, 0.5)
         mock_cycle.return_value = (20.0, 0.0)

         df = mock_market_data(days=100)
         strategy = FourierStrategy("TEST", df)

         result = strategy.analyze()
         assert result is not None
         assert "HIGH" in result['signal']

    @patch('option_auditor.strategies.fourier.calculate_dominant_cycle')
    @patch('option_auditor.strategies.fourier.calculate_hilbert_phase')
    def test_fourier_weak_cycle(self, mock_phase, mock_cycle, mock_market_data):
         # Strength < 0.02 -> WAIT (Weak Cycle)
         mock_phase.return_value = (np.pi, 0.01)
         mock_cycle.return_value = (20.0, 0.0)

         df = mock_market_data(days=100)
         strategy = FourierStrategy("TEST", df)

         result = strategy.analyze()
         assert result is not None
         assert "WAIT" in result['signal']
         assert "Weak" in result['signal']

# --- Functional Screener Tests ---

def test_calculate_hilbert_phase_math():
    # Simple test to ensure it runs without error on array
    prices = np.random.random(100) * 100
    phase, strength = calculate_hilbert_phase(prices)
    # Check bounds
    if phase is not None:
        assert -np.pi <= phase <= np.pi
        assert strength >= 0

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
@patch('option_auditor.strategies.fourier.calculate_hilbert_phase')
def test_screen_fourier_cycles_integration(mock_phase, mock_fetch):
    # Setup Data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100)
    prices = 100 + 10 * np.sin(np.linspace(0, 3.5*np.pi, 100)) # Bottoming
    df = pd.DataFrame({'Close': prices, 'High': prices+1, 'Low': prices-1, 'Volume': 1000}, index=dates)

    # Mock fetch to return this DF for a single ticker "CYC"
    # Note: fetch_batch_data_safe returns a DataFrame. If one ticker, columns might be flat or multiindex.
    # The screener runner handles single ticker iteration.
    mock_fetch.return_value = df

    # Mock phase to ensure it triggers a signal
    # Force a LOW signal
    mock_phase.return_value = (np.pi, 0.5)

    # Execute
    results = screen_fourier_cycles(ticker_list=["CYC"], region="us")

    # Verify
    assert len(results) == 1
    assert results[0]['ticker'] == "CYC"
    assert "LOW" in results[0]['signal']

@patch('option_auditor.common.screener_utils.fetch_batch_data_safe')
def test_screen_fourier_empty(mock_fetch):
    mock_fetch.return_value = pd.DataFrame()
    results = screen_fourier_cycles(ticker_list=["EMPTY"])
    assert len(results) == 0
