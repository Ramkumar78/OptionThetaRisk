import pytest
import pandas as pd
from option_auditor.risk_analyzer import check_itm_risk
from option_auditor.models import TradeGroup, Leg

# Mock prices
PRICES = {
    "XYZ": 95.0
}

def test_bull_put_spread_risk_not_flagged():
    """
    Test case: Bull Put Spread (Short 100 Put, Long 90 Put). Price 95.
    Short 100 Put: Intrinsic -500.
    Long 90 Put: Intrinsic 0.
    Net Intrinsic: -500.
    Threshold < -500.
    Should NOT be risky.
    """
    ts = pd.Timestamp.now()

    # Short 100 Put
    g1 = TradeGroup(contract_id="XYZ:::P100", symbol="XYZ", expiry=None, strike=100.0, right='P')
    g1.add_leg(Leg(ts=ts, qty=-1, price=0, fees=0, proceeds=0)) # Short 1

    # Long 90 Put
    g2 = TradeGroup(contract_id="XYZ:::P90", symbol="XYZ", expiry=None, strike=90.0, right='P')
    g2.add_leg(Leg(ts=ts, qty=1, price=0, fees=0, proceeds=0)) # Long 1

    open_groups = [g1, g2]

    risky, amount, details = check_itm_risk(open_groups, PRICES)

    # Assert
    assert not risky, f"Bull Put Spread at 95 (Short 100P, Long 90P) should NOT be flagged as risky. Details: {details}"

def test_bull_put_spread_deep_itm_is_risky():
    """
    Test case: Bull Put Spread (Short 100 Put, Long 90 Put). Price 80.
    Short 100 Put: (100-80)*-100 = -2000.
    Long 90 Put: (90-80)*100 = +1000.
    Net Intrinsic: -1000.
    Threshold < -500.
    Should BE risky.
    """
    ts = pd.Timestamp.now()
    prices_deep_itm = {"XYZ": 80.0}

    # Short 100 Put
    g1 = TradeGroup(contract_id="XYZ:::P100", symbol="XYZ", expiry=None, strike=100.0, right='P')
    g1.add_leg(Leg(ts=ts, qty=-1, price=0, fees=0, proceeds=0))

    # Long 90 Put
    g2 = TradeGroup(contract_id="XYZ:::P90", symbol="XYZ", expiry=None, strike=90.0, right='P')
    g2.add_leg(Leg(ts=ts, qty=1, price=0, fees=0, proceeds=0))

    open_groups = [g1, g2]

    risky, amount, details = check_itm_risk(open_groups, prices_deep_itm)

    # Assert
    assert risky, "Bull Put Spread deep ITM (Short 100P, Long 90P at 80) SHOULD be flagged as risky."
    assert amount == 1000.0

def test_short_put_unhedged_is_risky():
    """
    Test case: Short 100 Put. Price 94.
    Intrinsic: (100-94)*-100 = -600.
    Net: -600.
    Risky.
    """
    ts = pd.Timestamp.now()
    prices = {"XYZ": 94.0}

    g1 = TradeGroup(contract_id="XYZ:::P100", symbol="XYZ", expiry=None, strike=100.0, right='P')
    g1.add_leg(Leg(ts=ts, qty=-1, price=0, fees=0, proceeds=0))

    risky, amount, details = check_itm_risk([g1], prices)
    assert risky
    assert amount == 600.0

def test_covered_call_handling():
    """
    Test case: Short 100 Call, Long Stock (100 shares). Price 110.
    Short 100 Call: (110-100)*-100 = -1000.
    Long Stock: 100 shares at 110 = 11000 value.
    Net should include stock, so typically positive.
    This ensures we don't flag covered calls as risky.
    """
    ts = pd.Timestamp.now()
    prices = {"XYZ": 110.0}

    # Short 100 Call
    g1 = TradeGroup(contract_id="XYZ:::C100", symbol="XYZ", expiry=None, strike=100.0, right='C')
    g1.add_leg(Leg(ts=ts, qty=-1, price=0, fees=0, proceeds=0))

    # Long Stock
    g2 = TradeGroup(contract_id="XYZ:::STOCK", symbol="XYZ", expiry=None, strike=None, right=None)
    g2.add_leg(Leg(ts=ts, qty=100, price=0, fees=0, proceeds=0))

    risky, amount, details = check_itm_risk([g1, g2], prices)

    assert not risky, "Covered Call should NOT be risky if stock is accounted for."
