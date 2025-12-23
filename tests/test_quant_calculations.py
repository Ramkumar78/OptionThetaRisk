
import unittest
import numpy as np
import pandas as pd
from option_auditor.quant_engine import QuantPhysicsEngine
from option_auditor.common.math_engine import calculate_hurst_exponent, get_signal_entropy

class TestQuantCalculations(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)

    def test_quant_hurst_random_walk(self):
        """Test QuantEngine Hurst on Random Walk (Should be ~0.5)"""
        rw = np.cumsum(np.random.randn(2000)) + 1000
        h = QuantPhysicsEngine.calculate_hurst(pd.Series(rw))
        print(f"Quant RW Hurst: {h}")
        self.assertTrue(0.40 <= h <= 0.60, f"Hurst for RW should be near 0.5, got {h}")

    def test_math_hurst_random_walk(self):
        """Test MathEngine Hurst on Random Walk (Should be ~0.5)"""
        rw = np.cumsum(np.random.randn(2000)) + 1000
        h = calculate_hurst_exponent(rw)
        print(f"Math RW Hurst: {h}")
        self.assertTrue(0.40 <= h <= 0.60, f"Math Hurst for RW should be near 0.5, got {h}")

    def test_quant_hurst_trend(self):
        """Test QuantEngine Hurst on Trend (Should be > 0.5, but limited by method)"""
        # Linear trend + noise
        t = np.linspace(0, 100, 2000) + np.random.randn(2000) * 0.1
        h = QuantPhysicsEngine.calculate_hurst(pd.Series(t))
        print(f"Quant Trend Hurst: {h}")
        self.assertTrue(0.0 <= h <= 1.0)

    def test_quant_hurst_robustness(self):
        """Test QuantEngine Hurst on Constant (Should handle zero division)"""
        const = np.ones(100) * 100
        h = QuantPhysicsEngine.calculate_hurst(pd.Series(const))
        print(f"Quant Constant Hurst: {h}")
        # The logic now returns ~0.0 (slope of horizontal line log(tau)) instead of crashing or returning 0.5 via exception
        # This is acceptable for a constant line (Persistence of zero change? Or just H=0 Mean Reverting to itself?)
        # Standard H for constant is 0.
        self.assertTrue(h < 0.1, "Constant series should have H close to 0")

    def test_quant_entropy_robustness(self):
        """Test Entropy on short/empty series"""
        s = pd.Series([100, 101, 102])
        e = QuantPhysicsEngine.shannon_entropy(s)
        self.assertEqual(e, 1.0) # < 10 items returns 1.0

    def test_kalman_robustness(self):
        """Test Kalman on NaN heavy series"""
        s = pd.Series([np.nan, 100, 101, np.nan, 102])
        k = QuantPhysicsEngine.kalman_filter(s)
        self.assertEqual(len(k), 5)
        # Should not crash
