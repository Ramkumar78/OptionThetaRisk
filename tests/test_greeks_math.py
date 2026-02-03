import pytest
from option_auditor.strategies.math_utils import calculate_greeks

def test_calculate_greeks_call_atm():
    # ATM Call: S=100, K=100, T=1yr, r=5%, sigma=20%
    # Delta should be > 0.5 due to drift
    greeks = calculate_greeks(100, 100, 1, 0.05, 0.2, "call")

    assert 0.5 < greeks['delta'] < 0.7
    assert greeks['gamma'] > 0
    assert greeks['vega'] > 0
    assert greeks['theta'] < 0
    assert greeks['rho'] > 0

def test_calculate_greeks_put_atm():
    # ATM Put
    greeks = calculate_greeks(100, 100, 1, 0.05, 0.2, "put")

    # Delta should be < -0.3 (roughly -0.36)
    assert -0.5 < greeks['delta'] < 0
    assert greeks['gamma'] > 0 # Gamma is same for put/call
    assert greeks['vega'] > 0
    # Theta is usually negative but can be positive for deep ITM puts or high rates. ATM Put should be negative.
    assert greeks['theta'] < 0
    assert greeks['rho'] < 0

def test_calculate_greeks_itm_call():
    # Deep ITM Call: S=150, K=100
    greeks = calculate_greeks(150, 100, 1, 0.05, 0.2, "call")
    assert greeks['delta'] > 0.9

def test_calculate_greeks_otm_call():
    # Deep OTM Call: S=50, K=100
    greeks = calculate_greeks(50, 100, 1, 0.05, 0.2, "call")
    assert greeks['delta'] < 0.1

def test_expired_option():
    # T=0
    greeks = calculate_greeks(100, 100, 0, 0.05, 0.2, "call")
    assert greeks['delta'] == 0.0 # ATM expired is worthless if we check S > K strictly (100 > 100 False)

    # ITM Expired
    greeks = calculate_greeks(101, 100, 0, 0.05, 0.2, "call")
    assert greeks['delta'] == 1.0

    # OTM Expired
    greeks = calculate_greeks(99, 100, 0, 0.05, 0.2, "call")
    assert greeks['delta'] == 0.0
