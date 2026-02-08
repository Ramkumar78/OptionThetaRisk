import pytest
import pandas as pd
import numpy as np
import pandas_ta as ta
from option_auditor.strategies.isa import IsaStrategy
from unittest.mock import MagicMock, patch

# --- Helper to create mock data ---
def create_mock_data(days=300, price_start=100.0, trend="up", volatility=1.0):
    """
    Creates a mock OHLCV DataFrame.
    Trend: 'up' (linear increase), 'down' (linear decrease), 'flat' (constant), 'vcp' (contracting).
    """
    dates = pd.date_range(start='2020-01-01', periods=days, freq='B')

    if trend == "up":
        prices = np.linspace(price_start, price_start * 1.5, days)
    elif trend == "down":
        prices = np.linspace(price_start, price_start * 0.5, days)
    elif trend == "flat":
        prices = np.full(days, price_start)
    elif trend == "vcp":
        # Simulate VCP: Contracting volatility
        # Base price slightly uptrending
        base = np.linspace(price_start, price_start * 1.1, days)
        # Volatility decreases linearly from high to low
        vols = np.linspace(5.0, 0.5, days)
        # Ensure non-negative volatility for normal distribution
        vols = np.maximum(vols, 0.01)
        noise = np.array([np.random.normal(0, v) for v in vols])
        prices = base + noise
    else:
        prices = np.full(days, price_start)

    # OHLC Logic
    opens = prices
    closes = prices + np.random.normal(0, 0.1, days)
    highs = np.maximum(opens, closes) + (volatility * 0.5)
    lows = np.minimum(opens, closes) - (volatility * 0.5)
    volumes = np.random.randint(100000, 1000000, days)

    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)

    return df

class TestIsaLogic:

    def test_ema_alignment_bullish(self):
        """
        Test that EMA alignment (Price > 50 > 150 > 200) is correctly identified as Bullish.
        """
        # Create data where EMAs will align perfectly
        # A steady strong uptrend usually achieves this
        df = create_mock_data(days=400, price_start=100, trend="up")

        # Manually verify or force alignment if needed, but linear uptrend works well for EMAs
        # Let's verify mathematically:
        # EMA 50 will be closest to price, then 150, then 200.

        strategy = IsaStrategy("TEST", df)

        # We expect a method check_ema_alignment or similar to exist and return True/Bullish
        # Since I'm writing tests for code I will implement, I'll assume the method name.
        alignment = strategy.check_ema_alignment()

        assert alignment is True, "EMA Alignment should be True for strong uptrend"

    def test_ema_alignment_bearish(self):
        """
        Test that EMA alignment fails when trend is down or mixed.
        """
        df = create_mock_data(days=400, price_start=100, trend="down")
        strategy = IsaStrategy("TEST", df)

        alignment = strategy.check_ema_alignment()
        assert alignment is False, "EMA Alignment should be False for downtrend"

    def test_vcp_detection_success(self):
        """
        Test VCP detection on data with contracting volatility.
        """
        # Create data with contracting volatility (VCP)
        # Logic checks last 30 days in 10-day chunks.
        dates = pd.date_range(start='2020-01-01', periods=100, freq='B')

        # Indices 0-70: Noise
        p_base = np.random.normal(100, 5.0, 70)
        # Indices 70-80: High Vol (Period 3)
        p3 = np.random.normal(100, 5.0, 10)
        # Indices 80-90: Med Vol (Period 2)
        p2 = np.random.normal(100, 2.5, 10)
        # Indices 90-100: Low Vol (Period 1)
        p1 = np.random.normal(100, 0.5, 10)

        prices = np.concatenate([p_base, p3, p2, p1])

        df = pd.DataFrame({
            'Open': prices,
            'High': prices + 0.5,
            'Low': prices - 0.5,
            'Close': prices, # Close is most important
            'Volume': 1000
        }, index=dates)

        strategy = IsaStrategy("TEST", df)
        is_vcp = strategy.check_vcp()

        assert is_vcp, "Should detect VCP (contracting volatility)"

    def test_vcp_detection_fail_expanding(self):
        """
        Test VCP detection fails on expanding volatility.
        """
        dates = pd.date_range(start='2020-01-01', periods=100, freq='B')

        # Indices 0-70: Noise
        p_base = np.random.normal(100, 1.0, 70)
        # Indices 70-80: Low Vol
        p3 = np.random.normal(100, 1.0, 10)
        # Indices 80-90: Med Vol
        p2 = np.random.normal(100, 2.5, 10)
        # Indices 90-100: High Vol
        p1 = np.random.normal(100, 5.0, 10)

        prices = np.concatenate([p_base, p3, p2, p1])

        df = pd.DataFrame({
            'Open': prices,
            'High': prices + 0.5,
            'Low': prices - 0.5,
            'Close': prices,
            'Volume': 1000
        }, index=dates)

        strategy = IsaStrategy("TEST", df)
        is_vcp = strategy.check_vcp()

        assert not is_vcp, "Should NOT detect VCP (expanding volatility)"

    def test_relative_strength_ranking(self):
        """
        Test Relative Strength calculation against a mock benchmark.
        """
        # Mock Stock: +20% over last year
        dates = pd.date_range(start='2020-01-01', periods=252, freq='B')
        stock_prices = np.linspace(100, 120, 252) # +20%
        stock_df = pd.DataFrame({'Close': stock_prices, 'High': stock_prices, 'Low': stock_prices, 'Open': stock_prices, 'Volume': 1000}, index=dates)

        # Mock Benchmark: +10% over last year
        bench_prices = np.linspace(100, 110, 252) # +10%
        bench_df = pd.DataFrame({'Close': bench_prices}, index=dates)

        # Initialize strategy with benchmark
        # I assume I will update __init__ to accept benchmark_df
        strategy = IsaStrategy("TEST", stock_df, benchmark_df=bench_df)

        rs_score = strategy.calculate_relative_strength()

        # Expected: Stock outperformed benchmark significantly
        # If Logic is Ratio(Now) / Ratio(Start) or similar
        # Stock growth 1.2, Bench growth 1.1 -> RS > 0 or > 1 depending on formula.
        # Let's assume the method returns a float representing outperformance pct or similar.

        assert rs_score > 0, "RS Score should be positive when outperforming benchmark"

    def test_relative_strength_underperformance(self):
        """
        Test Relative Strength calculation when underperforming.
        """
        dates = pd.date_range(start='2020-01-01', periods=252, freq='B')
        stock_prices = np.linspace(100, 105, 252) # +5%
        stock_df = pd.DataFrame({'Close': stock_prices, 'High': stock_prices, 'Low': stock_prices, 'Open': stock_prices, 'Volume': 1000}, index=dates)

        bench_prices = np.linspace(100, 110, 252) # +10%
        bench_df = pd.DataFrame({'Close': bench_prices}, index=dates)

        strategy = IsaStrategy("TEST", stock_df, benchmark_df=bench_df)
        rs_score = strategy.calculate_relative_strength()

        assert rs_score < 0, "RS Score should be negative when underperforming benchmark"

    def test_relative_strength_missing_benchmark(self):
        """
        Test fallback when no benchmark is provided.
        """
        df = create_mock_data(days=200)
        strategy = IsaStrategy("TEST", df, benchmark_df=None) # Explicitly None

        rs_score = strategy.calculate_relative_strength()

        # Should default to 0 or handle gracefully
        assert rs_score == 0 or rs_score is None

    def test_analyze_integration(self):
        """
        Test that analyze() returns a dictionary containing the new metrics.
        """
        df = create_mock_data(days=300, trend="up")
        strategy = IsaStrategy("TEST", df)
        result = strategy.analyze()

        assert result is not None
        assert "ema_alignment" in result
        assert "vcp" in result
        assert "rs_rating" in result # or 'relative_strength'

    def test_edge_case_missing_data(self):
        """
        Test behavior with insufficient data for indicators (e.g. < 200 days).
        """
        df = create_mock_data(days=100) # Less than 200
        strategy = IsaStrategy("TEST", df)

        # EMA 200 requires 200 days.
        # Check explicit methods
        alignment = strategy.check_ema_alignment()
        assert alignment is False # Or None, but False is safer for boolean check

        # Analyze should probably return None or minimal dict
        result = strategy.analyze()
        assert result is None # Existing logic returns None if < 200 (or check_mode logic)
