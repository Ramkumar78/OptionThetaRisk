import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

@pytest.fixture
def mock_market_data():
    """Generates a flexible mock DataFrame for testing strategies."""
    def _generator(days=200, price=100.0, trend="flat", volatility=0.01):
        dates = pd.date_range(end=datetime.now(), periods=days)

        if trend == "up":
            prices = np.linspace(price, price * 1.5, days)
        elif trend == "down":
            prices = np.linspace(price, price * 0.5, days)
        else:
            prices = np.full(days, price)

        # Add noise
        noise = np.random.normal(0, price * volatility, days)
        close_prices = prices + noise

        # Ensure High/Low/Open match somewhat realistic OHLV
        high_prices = close_prices + (price * 0.02)
        low_prices = close_prices - (price * 0.02)
        open_prices = close_prices # simplify

        df = pd.DataFrame({
            'Open': open_prices,
            'High': high_prices,
            'Low': low_prices,
            'Close': close_prices,
            'Volume': np.random.randint(1000000, 5000000, days)
        }, index=dates)

        return df
    return _generator

@pytest.fixture
def mock_ticker_names():
    return {
        "AAPL": "Apple Inc.",
        "TSLA": "Tesla Inc.",
        "NVDA": "NVIDIA Corp"
    }
