from option_auditor.main_analyzer import _format_legs
from option_auditor.models import StrategyGroup, TradeGroup

def test_format_legs_basic():
    # Setup a mock strategy with simple legs
    s = StrategyGroup(id="test", symbol="SPY", expiry=None)

    # 390 Put
    tg1 = TradeGroup(contract_id="c1", symbol="SPY", expiry=None, strike=390.0, right="P")
    s.legs.append(tg1)

    # 400 Put
    tg2 = TradeGroup(contract_id="c2", symbol="SPY", expiry=None, strike=400.0, right="P")
    s.legs.append(tg2)

    result = _format_legs(s)
    # Expected: "390P/400P" (sorted alphabetically: "3" < "4")
    assert result == "390P/400P"

def test_format_legs_stock_and_option():
    s = StrategyGroup(id="test_cc", symbol="AAPL", expiry=None)

    # Stock
    tg_stock = TradeGroup(contract_id="stock", symbol="AAPL", expiry=None, strike=None, right=None)
    s.legs.append(tg_stock)

    # 150 Call
    tg_call = TradeGroup(contract_id="opt", symbol="AAPL", expiry=None, strike=150.0, right="C")
    s.legs.append(tg_call)

    result = _format_legs(s)
    # Expected: "150C/Stock" (sorted: "1" < "S")
    assert result == "150C/Stock"

def test_format_legs_duplicates():
    # Strategy that might have multiple legs of same contract (e.g. rolled or added to)
    s = StrategyGroup(id="test_dup", symbol="SPY", expiry=None)

    tg1 = TradeGroup(contract_id="c1", symbol="SPY", expiry=None, strike=390.0, right="P")
    s.legs.append(tg1)

    tg2 = TradeGroup(contract_id="c1", symbol="SPY", expiry=None, strike=390.0, right="P")
    s.legs.append(tg2)

    result = _format_legs(s)
    assert result == "390P"

def test_format_legs_float_strike():
    s = StrategyGroup(id="test_float", symbol="IWM", expiry=None)

    # 175.5 Call
    tg = TradeGroup(contract_id="c1", symbol="IWM", expiry=None, strike=175.5, right="C")
    s.legs.append(tg)

    result = _format_legs(s)
    assert result == "175.5C"

def test_format_legs_stock_only():
    s = StrategyGroup(id="test_stock", symbol="TSLA", expiry=None)
    tg = TradeGroup(contract_id="stock", symbol="TSLA", expiry=None, strike=None, right=None)
    s.legs.append(tg)

    result = _format_legs(s)
    assert result == "Stock"
