import pytest
import pandas as pd
from datetime import datetime
from option_auditor.models import StrategyGroup, TradeGroup

class TestStrategyMetrics:

    def test_hold_days_same_day_calculation(self):
        """
        Verify that hold_days returns a minimal value (0.001) for same-day entry and exit
        to prevent division by zero in average_daily_pnl.
        """
        sg = StrategyGroup(id="test_sg_same_day", symbol="AAPL", expiry=None)

        # Scenario: Entry and Exit are exactly the same timestamp
        ts = pd.Timestamp("2023-10-27 10:00:00")
        sg.entry_ts = ts
        sg.exit_ts = ts

        # hold_days should return max(0.0, 0.001) = 0.001
        assert sg.hold_days() == 0.001

        # Scenario: Entry and Exit are very close (e.g., 1 second difference)
        sg.exit_ts = ts + pd.Timedelta(seconds=1)
        # 1 second is approx 1.157e-5 days, which is < 0.001
        assert sg.hold_days() == 0.001

    def test_hold_days_normal_calculation(self):
        """
        Verify that hold_days returns the correct number of days for a standard duration.
        """
        sg = StrategyGroup(id="test_sg_normal", symbol="AAPL", expiry=None)

        start_ts = pd.Timestamp("2023-10-01 10:00:00")
        end_ts = pd.Timestamp("2023-10-03 22:00:00") # 2 days + 12 hours = 2.5 days

        sg.entry_ts = start_ts
        sg.exit_ts = end_ts

        expected_days = 2.5
        assert sg.hold_days() == expected_days

    def test_average_daily_pnl_calculation(self):
        """
        Verify average_daily_pnl calculation for normal duration.
        """
        sg = StrategyGroup(
            id="test_sg_pnl",
            symbol="AAPL",
            expiry=None,
            pnl=105.0,  # Gross PnL
            fees=5.0    # Fees
        )
        # Net PnL = 100.0

        start_ts = pd.Timestamp("2023-10-01 10:00:00")
        end_ts = pd.Timestamp("2023-10-06 10:00:00") # 5 days

        sg.entry_ts = start_ts
        sg.exit_ts = end_ts

        expected_daily_pnl = 100.0 / 5.0 # 20.0
        assert sg.average_daily_pnl() == expected_daily_pnl

    def test_average_daily_pnl_same_day(self):
        """
        Verify average_daily_pnl calculation for same-day trades uses the 0.001 floor
        and does not raise ZeroDivisionError.
        """
        sg = StrategyGroup(
            id="test_sg_pnl_same_day",
            symbol="AAPL",
            expiry=None,
            pnl=105.0,
            fees=5.0
        )
        # Net PnL = 100.0

        ts = pd.Timestamp("2023-10-27 10:00:00")
        sg.entry_ts = ts
        sg.exit_ts = ts

        # hold_days() returns 0.001
        expected_daily_pnl = 100.0 / 0.001
        assert sg.average_daily_pnl() == expected_daily_pnl

    def test_add_leg_group_integration(self):
        """
        Verify that add_leg_group correctly updates group-level timestamps and PnL
        from child TradeGroup objects.
        """
        sg = StrategyGroup(id="test_sg_integration", symbol="AAPL", expiry=None)

        # TradeGroup 1: Starts first, ends middle.
        ts1_start = pd.Timestamp("2023-01-01 10:00:00")
        ts1_end = pd.Timestamp("2023-01-05 10:00:00")
        tg1 = TradeGroup(
            contract_id="TG1",
            symbol="AAPL",
            expiry=None, strike=None, right=None,
            pnl=50.0,
            fees=2.0,
            entry_ts=ts1_start,
            exit_ts=ts1_end
        )

        sg.add_leg_group(tg1)

        assert sg.pnl == 50.0
        assert sg.fees == 2.0
        assert sg.entry_ts == ts1_start
        assert sg.exit_ts == ts1_end
        assert len(sg.legs) == 1

        # TradeGroup 2: Starts later, ends later.
        ts2_start = pd.Timestamp("2023-01-03 10:00:00")
        ts2_end = pd.Timestamp("2023-01-10 10:00:00")
        tg2 = TradeGroup(
            contract_id="TG2",
            symbol="AAPL",
            expiry=None, strike=None, right=None,
            pnl=30.0,
            fees=3.0,
            entry_ts=ts2_start,
            exit_ts=ts2_end
        )

        sg.add_leg_group(tg2)

        # Expected aggregates:
        # PnL: 50 + 30 = 80
        # Fees: 2 + 3 = 5
        # Entry: min(ts1_start, ts2_start) = ts1_start
        # Exit: max(ts1_end, ts2_end) = ts2_end

        assert sg.pnl == 80.0
        assert sg.fees == 5.0
        assert sg.entry_ts == ts1_start
        assert sg.exit_ts == ts2_end
        assert len(sg.legs) == 2

        # TradeGroup 3: Starts even earlier (updates entry_ts), ends early (no update to exit_ts)
        ts3_start = pd.Timestamp("2022-12-31 10:00:00")
        ts3_end = pd.Timestamp("2023-01-02 10:00:00")
        tg3 = TradeGroup(
            contract_id="TG3",
            symbol="AAPL",
            expiry=None, strike=None, right=None,
            pnl=10.0,
            fees=1.0,
            entry_ts=ts3_start,
            exit_ts=ts3_end
        )

        sg.add_leg_group(tg3)

        assert sg.pnl == 90.0
        assert sg.fees == 6.0
        assert sg.entry_ts == ts3_start  # Updated to earlier date
        assert sg.exit_ts == ts2_end     # Remains latest date
        assert len(sg.legs) == 3

    def test_average_daily_pnl_missing_timestamps(self):
        """
        Verify behavior when timestamps are missing. Currently raises ZeroDivisionError.
        This test documents current behavior (or validates fix if applied).
        """
        sg = StrategyGroup(id="test_sg_missing_ts", symbol="AAPL", expiry=None)
        # No timestamps set -> hold_days() returns 0.0 -> ZeroDivisionError

        with pytest.raises(ZeroDivisionError):
            sg.average_daily_pnl()
