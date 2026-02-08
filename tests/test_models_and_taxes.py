import pytest
import datetime
import pandas as pd
from option_auditor.models import TradeGroup, Leg, StrategyGroup, calculate_regulatory_fees

class TestTradeGroup:
    def test_add_leg_updates_state(self):
        # Create a TradeGroup
        tg = TradeGroup(
            contract_id="TEST-1",
            symbol="TEST",
            expiry=pd.Timestamp("2023-12-31"),
            strike=100.0,
            right="C"
        )

        # Create Legs
        ts1 = pd.Timestamp("2023-01-01 10:00:00")
        leg1 = Leg(
            ts=ts1,
            qty=1.0,
            price=10.0,
            fees=0.5,
            proceeds=-1000.0, # Buy 1 call @ 10
            description="Buy Call"
        )

        ts2 = pd.Timestamp("2023-01-02 10:00:00")
        leg2 = Leg(
            ts=ts2,
            qty=-1.0,
            price=12.0,
            fees=0.5,
            proceeds=1200.0, # Sell 1 call @ 12
            description="Sell Call"
        )

        # Test add_leg 1
        tg.add_leg(leg1)
        assert len(tg.legs) == 1
        assert tg.qty_net == 1.0
        assert tg.pnl == -1000.0
        assert tg.fees == 0.5
        assert tg.entry_ts == ts1
        assert tg.exit_ts == ts1

        # Test add_leg 2
        tg.add_leg(leg2)
        assert len(tg.legs) == 2
        assert tg.qty_net == 0.0
        assert tg.pnl == 200.0 # -1000 + 1200
        assert tg.fees == 1.0 # 0.5 + 0.5
        assert tg.entry_ts == ts1
        assert tg.exit_ts == ts2
        assert tg.net_pnl == 199.0 # 200 - 1

    def test_is_closed_epsilon(self):
        tg = TradeGroup(contract_id="TEST-2", symbol="TEST", expiry=None, strike=None, right=None)

        # Case 1: Exactly 0.0
        tg.qty_net = 0.0
        assert tg.is_closed is True

        # Case 2: Floating point accumulation error
        # Simulate 0.1 + 0.2 - 0.3 which often results in non-zero float
        tg.qty_net = 0.1 + 0.2 - 0.3
        # Verify it's not exactly 0 if python behaves as expected
        # Usually it is 5.551115123125783e-17
        assert abs(tg.qty_net) < 1e-9
        assert tg.is_closed is True

        # Case 3: Slightly larger but still closed
        tg.qty_net = 1e-10
        assert tg.is_closed is True

        # Case 4: Not closed
        tg.qty_net = 1e-8
        assert tg.is_closed is False

        tg.qty_net = -1e-8
        assert tg.is_closed is False

class TestStrategyGroup:
    def test_average_daily_pnl(self):
        sg = StrategyGroup(id="SG-1", symbol="TEST", expiry=None)

        # Create a TradeGroup to add
        tg = TradeGroup(contract_id="TG-1", symbol="TEST", expiry=None, strike=None, right=None)

        ts_entry = pd.Timestamp("2023-01-01 10:00:00")
        ts_exit = pd.Timestamp("2023-01-11 10:00:00") # 10 days later

        # Manually set properties to simulate added legs
        tg.entry_ts = ts_entry
        tg.exit_ts = ts_exit
        tg.pnl = 2000.0
        tg.fees = 100.0

        sg.add_leg_group(tg)

        assert sg.entry_ts == ts_entry
        assert sg.exit_ts == ts_exit
        assert sg.pnl == 2000.0
        assert sg.fees == 100.0
        assert sg.net_pnl == 1900.0

        # hold_days should be 10.0
        expected_hold_days = 10.0
        assert abs(sg.hold_days() - expected_hold_days) < 1e-6

        # Average Daily PnL = Net PnL / Hold Days
        expected_avg_daily = 1900.0 / 10.0 # 190.0
        assert abs(sg.average_daily_pnl() - expected_avg_daily) < 1e-6

class TestRegulatoryFees:
    def test_uk_stamp_duty(self):
        symbol = "VOD.L"
        price = 100.0
        qty = 10.0
        val = 1000.0

        # UK Stock BUY -> 0.5%
        fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="stock")
        assert fees == val * 0.005

        # UK Stock OPEN -> 0.5%
        fees = calculate_regulatory_fees(symbol, price, qty, action="OPEN", asset_class="stock")
        assert fees == val * 0.005

        # UK Stock SELL -> 0.0%
        fees = calculate_regulatory_fees(symbol, price, qty, action="SELL", asset_class="stock")
        assert fees == 0.0

        # UK Option BUY -> 0.0%
        fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="option")
        assert fees == 0.0

    def test_india_stt(self):
        symbols = ["RELIANCE.NS", "TCS.BO"]
        price = 1000.0
        qty = 1.0
        val = 1000.0

        for symbol in symbols:
            # India Stock BUY -> 0.1%
            fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="stock")
            assert fees == val * 0.001

            # India Stock SELL -> 0.1%
            fees = calculate_regulatory_fees(symbol, price, qty, action="SELL", asset_class="stock")
            assert fees == val * 0.001

            # India Option -> 0.0% (per current implementation assumption)
            fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="option")
            assert fees == 0.0

    def test_us_no_fees(self):
        symbol = "AAPL"
        price = 150.0
        qty = 10.0

        # US Stock BUY
        fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="stock")
        assert fees == 0.0

        # US Stock SELL
        fees = calculate_regulatory_fees(symbol, price, qty, action="SELL", asset_class="stock")
        assert fees == 0.0

        # US Option
        fees = calculate_regulatory_fees(symbol, price, qty, action="BUY", asset_class="option")
        assert fees == 0.0
