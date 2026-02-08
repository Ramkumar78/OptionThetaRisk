import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime
from option_auditor.parsers import TastytradeFillsParser

# Save real datetime to use in side effects
real_datetime = datetime

class TestTastytradeFillsParserLogic:
    def setup_method(self):
        self.parser = TastytradeFillsParser()

    def test_regex_multileg_extraction(self):
        # Description with multiple legs
        # Adjusted to match regex: `qty month day ... strike right action`
        # Example:
        # -1 NOV 18 100.0 PUT SELL
        # 1 NOV 18 110.0 PUT BUY
        description = "-1 NOV 18 100.0 PUT SELL\n1 NOV 18 110.0 PUT BUY"

        # DataFrame setup
        df = pd.DataFrame([{
            "Description": description,
            "Price": "1.50", # Total price
            "Symbol": "SPY",
            "Time": "2023-11-15 10:00:00",
            "Commissions": "2.00",
            "Fees": "0.10"
        }])

        parsed = self.parser.parse(df)

        # Verify 2 rows returned
        assert len(parsed) == 2

        # Check first leg (Short Put 100)
        # Note: Order is preserved from description lines
        leg1 = parsed.iloc[0]
        assert leg1['symbol'] == "SPY"
        assert leg1['qty'] == -1.0
        assert leg1['strike'] == 100.0
        assert leg1['right'] == "P"
        # Verify expiry: Trade is Nov 15 2023. Expiry is Nov 18. Should be 2023.
        assert leg1['expiry'].year == 2023
        assert leg1['expiry'].month == 11
        assert leg1['expiry'].day == 18

        # Check second leg (Long Put 110)
        leg2 = parsed.iloc[1]
        assert leg2['symbol'] == "SPY"
        assert leg2['qty'] == 1.0
        assert leg2['strike'] == 110.0
        assert leg2['right'] == "P"
        assert leg2['expiry'].year == 2023
        assert leg2['expiry'].month == 11
        assert leg2['expiry'].day == 18

    def test_fee_proceeds_splitting(self):
        # 2 legs, different quantities
        # Leg 1: Qty 1
        # Leg 2: Qty 2
        # Total Qty: 3
        # Ratio: 1/3 and 2/3
        description = "1 NOV 18 100.0 CALL BUY\n2 NOV 18 105.0 CALL BUY"
        total_price = 3.00 # Raw price 3.00. Code: raw_val * 100.0 -> 300.0. "Buy" -> Debit -> -300.0?
        # Code logic:
        # price_raw = "3.00"
        # is_credit = "cr" in price_raw (False)
        # raw_val = 3.00
        # total_money = 300.0
        # if not is_credit: total_money = -300.0
        # So Proceeds = -300.0

        commissions = 6.00
        fees = 0.30

        df = pd.DataFrame([{
            "Description": description,
            "Price": str(total_price),
            "Symbol": "SPY",
            "Time": "2023-11-15 10:00:00",
            "Commissions": str(commissions),
            "Fees": str(fees)
        }])

        parsed = self.parser.parse(df)

        assert len(parsed) == 2

        # Leg 1
        leg1 = parsed.iloc[0]
        assert leg1['qty'] == 1.0
        assert leg1['proceeds'] == pytest.approx(-100.0)
        expected_fees1 = (6.00 + 0.30) * (1/3)
        assert leg1['fees'] == pytest.approx(2.10)

        # Leg 2
        leg2 = parsed.iloc[1]
        assert leg2['qty'] == 2.0
        assert leg2['proceeds'] == pytest.approx(-200.0)
        expected_fees2 = (6.00 + 0.30) * (2/3)
        assert leg2['fees'] == pytest.approx(4.20)

    def test_expiry_year_crossover(self):
        # Trade date: Nov 15 2023
        # Expiry: Jan 20 (Month < 3)
        # Description matches regex: Qty Mon Day ...
        description = "1 JAN 20 100.0 CALL BUY"

        df = pd.DataFrame([{
            "Description": description,
            "Price": "1.00",
            "Symbol": "SPY",
            "Time": "2023-11-15 10:00:00",
            "Commissions": "0",
            "Fees": "0"
        }])

        parsed = self.parser.parse(df)
        leg = parsed.iloc[0]

        # Expiry year should be 2024
        assert leg['expiry'].year == 2024
        assert leg['expiry'].month == 1
        assert leg['expiry'].day == 20

    def test_date_adjustment_future_logic(self):
        # We need to mock datetime within option_auditor.parsers
        # Target: _parse_tasty_datetime
        # Logic: if dt > now + 2 days: year - 1

        fixed_now = real_datetime(2023, 1, 1, 12, 0, 0)

        with patch('option_auditor.parsers.datetime') as mock_dt:
            # Configure mock to behave like datetime class
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime.side_effect = real_datetime.strptime
            # Constructor call side effect
            mock_dt.side_effect = lambda *args, **kwargs: real_datetime(*args, **kwargs)

            # Input date: 2023-01-04 (Now + 3 days)
            # Should trigger year adjustment -> 2022-01-04

            # The input string "2023-01-04 10:00:00" parses to 2023-01-04
            # 2023-01-04 > 2023-01-01 + 2 days (2023-01-03)
            # So year becomes 2022

            dt = self.parser._parse_tasty_datetime("2023-01-04 10:00:00")
            assert dt.year == 2022
            assert dt.month == 1
            assert dt.day == 4

    def test_tasty_fills_parser_date_adjustment(self):
        # Verify that TastytradeFillsParser.parse actually uses the adjustment logic
        fixed_now = real_datetime(2023, 1, 1, 12, 0, 0)

        with patch('option_auditor.parsers.datetime') as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime.side_effect = real_datetime.strptime
            mock_dt.side_effect = lambda *args, **kwargs: real_datetime(*args, **kwargs)

            # DataFrame with future date in Time column
            # Description must be valid for parsing to return rows
            description = "1 JAN 20 100.0 CALL BUY"
            df = pd.DataFrame([{
                "Time": "2023-01-04 10:00:00",
                "Symbol": "SPY",
                "Description": description,
                "Price": "1.00",
                "Commissions": "0",
                "Fees": "0"
            }])

            parsed = self.parser.parse(df)

            # The 'datetime' column should be adjusted (2022)
            # Expiry year logic uses trade_year.
            # Trade year becomes 2022. Expiry (Jan 20) is month 1. Trade month 1.
            # Logic: if ts.month > 10 and month_num < 3: expiry_year += 1.
            # Here ts.month is 1. So expiry_year = trade_year = 2022.

            assert parsed.iloc[0]['datetime'].year == 2022
            assert parsed.iloc[0]['expiry'].year == 2022


# TastytradeParser does not use _parse_tasty_datetime for its Time column (uses pd.to_datetime directly),
# so we do not test date adjustment for it.
