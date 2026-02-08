import pytest
from option_auditor.models import calculate_regulatory_fees

def test_indian_stt_fees():
    """
    Test Indian STT (0.1%) for .NS and .BO symbols.
    Applied on both Buy and Sell for Delivery (current implementation applies unconditionally to 'stock').
    """
    price = 100.0
    qty = 10
    expected_fee = abs(price * qty) * 0.001 # 1.0

    # .NS Symbol - BUY
    fee_ns_buy = calculate_regulatory_fees("RELIANCE.NS", price, qty, action="BUY", asset_class="stock")
    assert fee_ns_buy == expected_fee

    # .NS Symbol - SELL
    fee_ns_sell = calculate_regulatory_fees("RELIANCE.NS", price, qty, action="SELL", asset_class="stock")
    assert fee_ns_sell == expected_fee

    # .BO Symbol - BUY
    fee_bo_buy = calculate_regulatory_fees("TCS.BO", price, qty, action="BUY", asset_class="stock")
    assert fee_bo_buy == expected_fee

    # .BO Symbol - SELL
    fee_bo_sell = calculate_regulatory_fees("TCS.BO", price, qty, action="SELL", asset_class="stock")
    assert fee_bo_sell == expected_fee

def test_uk_stamp_duty():
    """
    Test UK Stamp Duty (0.5%) for .L symbols.
    Only applied on BUY or OPEN actions.
    """
    price = 10.0
    qty = 100
    expected_fee = abs(price * qty) * 0.005 # 5.0

    # .L Symbol - BUY
    fee_l_buy = calculate_regulatory_fees("LLOY.L", price, qty, action="BUY", asset_class="stock")
    assert fee_l_buy == expected_fee

    # .L Symbol - OPEN
    fee_l_open = calculate_regulatory_fees("VOD.L", price, qty, action="OPEN", asset_class="stock")
    assert fee_l_open == expected_fee

    # .L Symbol - SELL (Should be 0)
    fee_l_sell = calculate_regulatory_fees("BARC.L", price, qty, action="SELL", asset_class="stock")
    assert fee_l_sell == 0.0

    # .L Symbol - CLOSE (Should be 0)
    fee_l_close = calculate_regulatory_fees("AZN.L", price, qty, action="CLOSE", asset_class="stock")
    assert fee_l_close == 0.0

def test_us_stocks_no_fees():
    """
    Ensure no fees are applied to standard US stocks by default.
    """
    price = 150.0
    qty = 10

    # US Symbol (No suffix) - BUY
    fee_us_buy = calculate_regulatory_fees("AAPL", price, qty, action="BUY", asset_class="stock")
    assert fee_us_buy == 0.0

    # US Symbol (No suffix) - SELL
    fee_us_sell = calculate_regulatory_fees("GOOGL", price, qty, action="SELL", asset_class="stock")
    assert fee_us_sell == 0.0

    # Other suffix not in list
    fee_other = calculate_regulatory_fees("ABC.TO", price, qty, action="BUY", asset_class="stock")
    assert fee_other == 0.0

def test_asset_class_distinction():
    """
    Verify the asset_class parameter distinguishes between stocks and options correctly.
    Mainly relevant for Indian STT where options might be exempt or treated differently (here we expect 0 fees for non-stock).
    """
    price = 100.0
    qty = 10

    # Indian Option - Should be 0 based on implementation checking asset_class.lower() == 'stock'
    fee_ns_opt = calculate_regulatory_fees("NIFTY.NS", price, qty, action="BUY", asset_class="option")
    assert fee_ns_opt == 0.0

    # UK Option - Should be 0 to ensure fee differentiation (fixed logic).
    fee_l_opt = calculate_regulatory_fees("LLOY.L", price, qty, action="BUY", asset_class="option")
    assert fee_l_opt == 0.0
