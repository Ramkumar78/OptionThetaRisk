import pytest
from option_auditor.models import calculate_regulatory_fees

def test_indian_stt_stock():
    """Verify Indian STT (0.1%) for .NS and .BO stocks on both BUY and SELL."""
    price = 1000.0
    qty = 10
    val = price * qty
    expected_fee = val * 0.001  # 10.0

    # .NS Stock BUY
    fee = calculate_regulatory_fees("RELIANCE.NS", price, qty, "BUY", "stock")
    assert fee == expected_fee, "Should apply 0.1% STT on Indian Stock BUY (.NS)"

    # .NS Stock SELL
    fee = calculate_regulatory_fees("RELIANCE.NS", price, qty, "SELL", "stock")
    assert fee == expected_fee, "Should apply 0.1% STT on Indian Stock SELL (.NS)"

    # .BO Stock BUY
    fee = calculate_regulatory_fees("TCS.BO", price, qty, "BUY", "stock")
    assert fee == expected_fee, "Should apply 0.1% STT on Indian Stock BUY (.BO)"

def test_indian_stt_option_exemption():
    """Verify Indian Options are exempt from STT (in this logic)."""
    price = 100.0
    qty = 50
    # Option should be 0 based on current implementation
    fee = calculate_regulatory_fees("NIFTY.NS", price, qty, "BUY", "option")
    assert fee == 0.0, "Indian Options should be exempt from STT"

def test_uk_stamp_duty_stock():
    """Verify UK Stamp Duty (0.5%) for .L stocks on BUY only."""
    price = 200.0
    qty = 100
    val = price * qty
    expected_fee = val * 0.005  # 100.0

    # .L Stock BUY
    fee = calculate_regulatory_fees("LLOY.L", price, qty, "BUY", "stock")
    assert fee == expected_fee, "Should apply 0.5% Stamp Duty on UK Stock BUY"

    # .L Stock SELL (No fee)
    fee = calculate_regulatory_fees("LLOY.L", price, qty, "SELL", "stock")
    assert fee == 0.0, "UK Stock SELL should be exempt from Stamp Duty"

def test_uk_stamp_duty_option_exemption():
    """Verify UK Options are exempt from Stamp Duty to ensure fee differentiation."""
    price = 5.0
    qty = 1000
    # Option should be 0 (differentiation requirement)
    # This test is expected to FAIL with current implementation.
    fee = calculate_regulatory_fees("LLOY.L", price, qty, "BUY", "option")
    assert fee == 0.0, "UK Options should be exempt from Stamp Duty (differentiation)"

def test_asset_class_differentiation_general():
    """Verify that changing asset_class from 'stock' to 'option' changes fee outcome where applicable."""
    price = 100.0
    qty = 10

    # India
    stock_fee = calculate_regulatory_fees("INFY.NS", price, qty, "BUY", "stock")
    option_fee = calculate_regulatory_fees("INFY.NS", price, qty, "BUY", "option")
    assert stock_fee > 0
    assert option_fee == 0
    assert stock_fee != option_fee, "Indian fees should differentiate by asset class"

    # UK (Expected behavior after fix)
    stock_fee_uk = calculate_regulatory_fees("VOD.L", price, qty, "BUY", "stock")
    option_fee_uk = calculate_regulatory_fees("VOD.L", price, qty, "BUY", "option")
    assert stock_fee_uk > 0
    # Until fix, option_fee_uk will be > 0, so this assertion will fail.
    assert option_fee_uk == 0
    assert stock_fee_uk != option_fee_uk, "UK fees should differentiate by asset class"
