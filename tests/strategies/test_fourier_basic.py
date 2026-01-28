import pytest
import pandas as pd
import numpy as np
from option_auditor.strategies.fourier import FourierStrategy

def test_fourier_analysis_structure():
    # Simple test to verify the strategy runs and returns expected structure
    dates = pd.date_range(start="2023-01-01", periods=100)
    # Create a sine wave
    x = np.linspace(0, 4*np.pi, 100)
    y = np.sin(x) + 100

    df = pd.DataFrame({'Close': y, 'High': y+1, 'Low': y-1, 'Open': y}, index=dates)

    strategy = FourierStrategy("TEST", df)
    result = strategy.analyze()

    assert result is not None
    assert 'cycle_phase' in result
    assert 'cycle_strength' in result
    assert 'signal' in result
    assert 'price' in result

def test_fourier_short_data():
    dates = pd.date_range(start="2023-01-01", periods=10)
    df = pd.DataFrame({'Close': np.random.rand(10)}, index=dates)

    strategy = FourierStrategy("TEST", df)
    result = strategy.analyze()

    assert result is None
