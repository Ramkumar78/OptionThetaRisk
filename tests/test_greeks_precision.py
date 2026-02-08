import pytest
import numpy as np
from option_auditor.strategies.math_utils import calculate_greeks, calculate_option_price

class TestGreeksPrecision:
    """
    Exhaustive tests for Black-Scholes Greeks and Option Pricing precision.
    Validates against known benchmarks and edge cases.
    """

    def test_benchmark_call_atm(self):
        """
        Benchmark Case: ATM Call Option
        S=100, K=100, T=1, r=0.05, sigma=0.2

        Reference Values (calculated via standard BS formula):
        Price: ~10.4506
        Delta: ~0.6368
        Gamma: ~0.01876
        Vega (1%): ~0.3752
        Theta (Daily): ~-0.01757 (Annual: -6.414)
        Rho (1%): ~0.5323
        """
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2

        # Test Price
        price = calculate_option_price(S, K, T, r, sigma, "call")
        assert price == pytest.approx(10.4506, abs=1e-4)

        # Test Greeks
        greeks = calculate_greeks(S, K, T, r, sigma, "call")

        assert greeks["delta"] == pytest.approx(0.6368, abs=1e-4)
        assert greeks["gamma"] == pytest.approx(0.01876, abs=1e-5)
        assert greeks["vega"] == pytest.approx(0.3752, abs=1e-4)
        assert greeks["theta"] == pytest.approx(-0.01757, abs=1e-5)
        assert greeks["rho"] == pytest.approx(0.5323, abs=1e-4)

    def test_benchmark_put_atm(self):
        """
        Benchmark Case: ATM Put Option
        S=100, K=100, T=1, r=0.05, sigma=0.2

        Reference Values:
        Price: ~5.5735
        Delta: ~-0.3632
        Gamma: ~0.01876 (Same as Call)
        Vega (1%): ~0.3752 (Same as Call)
        Theta (Daily): ~-0.00454 (Annual: -1.658)
        Rho (1%): ~-0.4189
        """
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2

        # Test Price
        price = calculate_option_price(S, K, T, r, sigma, "put")
        assert price == pytest.approx(5.5735, abs=1e-4)

        # Test Greeks
        greeks = calculate_greeks(S, K, T, r, sigma, "put")

        assert greeks["delta"] == pytest.approx(-0.3632, abs=1e-4)
        assert greeks["gamma"] == pytest.approx(0.01876, abs=1e-5)
        assert greeks["vega"] == pytest.approx(0.3752, abs=1e-4)
        assert greeks["theta"] == pytest.approx(-0.00454, abs=1e-5)
        assert greeks["rho"] == pytest.approx(-0.4189, abs=1e-4)

    def test_put_call_parity(self):
        """
        Verify Put-Call Parity: C - P = S - K * exp(-rT)
        """
        # Random inputs
        np.random.seed(42)
        for _ in range(10):
            S = np.random.uniform(50, 150)
            K = np.random.uniform(50, 150)
            T = np.random.uniform(0.1, 2.0)
            r = np.random.uniform(0.01, 0.1)
            sigma = np.random.uniform(0.1, 0.5)

            call_price = calculate_option_price(S, K, T, r, sigma, "call")
            put_price = calculate_option_price(S, K, T, r, sigma, "put")

            lhs = call_price - put_price
            rhs = S - K * np.exp(-r * T)

            assert lhs == pytest.approx(rhs, abs=1e-4), f"Parity failed for S={S}, K={K}, T={T}, r={r}, sigma={sigma}"

    def test_extreme_expiry(self):
        """
        Test T approaching 0 and T=0.
        """
        S, K, r, sigma = 100.0, 100.0, 0.05, 0.2

        # T -> 0 (Very small time)
        T_small = 1e-5

        # Call ITM (S > K)
        S_itm = 105.0
        greeks_itm = calculate_greeks(S_itm, K, T_small, r, sigma, "call")
        price_itm = calculate_option_price(S_itm, K, T_small, r, sigma, "call")

        assert greeks_itm["delta"] == pytest.approx(1.0, abs=0.1) # Should be close to 1
        assert price_itm == pytest.approx(5.0, abs=0.1) # Close to intrinsic

        # Call OTM (S < K)
        S_otm = 95.0
        greeks_otm = calculate_greeks(S_otm, K, T_small, r, sigma, "call")
        price_otm = calculate_option_price(S_otm, K, T_small, r, sigma, "call")

        assert greeks_otm["delta"] == pytest.approx(0.0, abs=0.1)
        assert price_otm == pytest.approx(0.0, abs=0.1)

        # T = 0 (Expired)
        # ITM Call
        greeks_expired_itm = calculate_greeks(105.0, 100.0, 0, 0.05, 0.2, "call")
        assert greeks_expired_itm["delta"] == 1.0
        assert greeks_expired_itm["gamma"] == 0.0

        # OTM Call
        greeks_expired_otm = calculate_greeks(95.0, 100.0, 0, 0.05, 0.2, "call")
        assert greeks_expired_otm["delta"] == 0.0

    def test_deep_itm_otm(self):
        """
        Test Deep ITM and OTM behaviors.
        """
        K, T, r, sigma = 100.0, 1.0, 0.05, 0.2

        # Deep ITM Call (S >> K)
        S_deep_itm = 2000.0
        greeks = calculate_greeks(S_deep_itm, K, T, r, sigma, "call")
        assert greeks["delta"] == pytest.approx(1.0, abs=1e-4)
        assert greeks["gamma"] == pytest.approx(0.0, abs=1e-4)

        # Deep OTM Call (S << K)
        S_deep_otm = 1.0
        greeks = calculate_greeks(S_deep_otm, K, T, r, sigma, "call")
        assert greeks["delta"] == pytest.approx(0.0, abs=1e-4)
        assert greeks["gamma"] == pytest.approx(0.0, abs=1e-4)

    def test_volatility_extremes(self):
        """
        Test high and low volatility.
        """
        S, K, T, r = 100.0, 100.0, 1.0, 0.05

        # Low Volatility (Approaching 0)
        sigma_low = 1e-4
        price_low = calculate_option_price(S, K, T, r, sigma_low, "call")
        # Should approach intrinsic value (plus interest rate effect)
        # For ATM Call: S - K*exp(-rT) approx if S > K*exp(-rT), else 0?
        # ATM: S=100, K=100. Intrinsic is 0. But strictly it's max(0, S - K*exp(-rT))? No, BS price converges to max(0, S - K*e^-rT) as sigma->0?
        # Let's check: d1 -> +inf if S > K*e^(-rT), -inf if S < K*e^(-rT).
        # S=100, K*e^-0.05 = 95.12. S > K*e^-rT. So d1 -> +inf. N(d1) -> 1.
        # Price -> S - K*e^-rT = 100 - 95.12 = 4.88.
        assert price_low == pytest.approx(100.0 - 100.0 * np.exp(-0.05), abs=0.1)

        # High Volatility
        sigma_high = 10.0 # 1000%
        price_high = calculate_option_price(S, K, T, r, sigma_high, "call")
        # Price should be close to S (stock price) for Call as vol -> infinity?
        # Actually max price for call is S.
        assert price_high == pytest.approx(100.0, abs=10.0) # Looser bound
        assert price_high < 100.0 + 1e-9 # Cannot exceed stock price

    def test_invalid_inputs(self):
        """
        Test invalid inputs like negative T or sigma.
        """
        # Negative T -> Should act as expired
        price_neg_t = calculate_option_price(100, 100, -1, 0.05, 0.2, "call")
        assert price_neg_t == 0.0 # Intrinsic is 0 for ATM

        # Negative Sigma -> Should be clamped to small positive
        # If sigma is clamped to 1e-5, it behaves like low vol.
        price_neg_sigma = calculate_option_price(100, 100, 1, 0.05, -0.2, "call")
        expected_low_vol = calculate_option_price(100, 100, 1, 0.05, 1e-5, "call")
        assert price_neg_sigma == pytest.approx(expected_low_vol, abs=1e-9)

    def test_division_by_zero_guards(self):
        """
        Ensure no ZeroDivisionError.
        """
        # Sigma = 0
        try:
            calculate_greeks(100, 100, 1, 0.05, 0, "call")
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for sigma=0")

        # T = 0
        try:
            calculate_greeks(100, 100, 0, 0.05, 0.2, "call")
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for T=0")

    def test_greek_signs(self):
        """
        Verify expected signs of Greeks.
        """
        S, K, T, r, sigma = 100.0, 100.0, 0.5, 0.05, 0.2

        # Long Call
        greeks_call = calculate_greeks(S, K, T, r, sigma, "call")
        assert greeks_call["delta"] > 0
        assert greeks_call["gamma"] > 0
        assert greeks_call["vega"] > 0
        assert greeks_call["theta"] < 0 # Usually negative for ATM
        assert greeks_call["rho"] > 0

        # Long Put
        greeks_put = calculate_greeks(S, K, T, r, sigma, "put")
        assert greeks_put["delta"] < 0
        assert greeks_put["gamma"] > 0 # Gamma is positive for long options
        assert greeks_put["vega"] > 0 # Vega is positive for long options
        assert greeks_put["theta"] < 0 # Usually negative
        assert greeks_put["rho"] < 0
