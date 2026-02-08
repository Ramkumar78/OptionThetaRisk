import unittest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from option_auditor.parsers import TastytradeParser, TastytradeFillsParser

class TestTastyFormats(unittest.TestCase):
    def setUp(self):
        self.fills_parser = TastytradeFillsParser()
        self.tasty_parser = TastytradeParser()

    def test_fills_complex_legs(self):
        # Description for an Iron Condor (4 legs)
        # Regex expects: Qty Month Day [DTE] Strike Right Action
        # e.g. "-1 Nov 17 450 Call BTO"
        description = """-1 Nov 17 450 Call BTO
        1 Nov 17 455 Call BTO
        -1 Nov 17 430 Put BTO
        1 Nov 17 425 Put BTO"""

        df = pd.DataFrame([{
            "Date": "11/17/2023",
            "Description": description,
            "Symbol": "SPY",
            "Quantity": 4, # Total legs? Or irrelevant for fills parser as it recalculates?
            "Price": "0.00", # Usually net credit/debit
            "Amount": "0.00",
            "Commission": "0.00",
            "Fees": "0.00",
            "Time": "10:00:00"
        }])

        # Mock current year to 2023 for consistent parsing
        with patch('option_auditor.parsers.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2023, 11, 15)
            # side_effect is needed because strptime is also called on datetime class
            mock_dt.strptime.side_effect = datetime.strptime

            result = self.fills_parser.parse(df)

        # Expect 4 rows
        self.assertEqual(len(result), 4)

        # Verify legs
        # -1 450 Call
        leg1 = result[(result['strike'] == 450.0) & (result['right'] == 'C')]
        self.assertEqual(len(leg1), 1)
        self.assertEqual(leg1.iloc[0]['qty'], -1.0)

        # 1 455 Call
        leg2 = result[(result['strike'] == 455.0) & (result['right'] == 'C')]
        self.assertEqual(len(leg2), 1)
        self.assertEqual(leg2.iloc[0]['qty'], 1.0)

        # -1 430 Put
        leg3 = result[(result['strike'] == 430.0) & (result['right'] == 'P')]
        self.assertEqual(len(leg3), 1)
        self.assertEqual(leg3.iloc[0]['qty'], -1.0)

        # 1 425 Put
        leg4 = result[(result['strike'] == 425.0) & (result['right'] == 'P')]
        self.assertEqual(len(leg4), 1)
        self.assertEqual(leg4.iloc[0]['qty'], 1.0)


    def test_datetime_parsing_logic(self):
        # 1. AM/PM Handling
        # We use explicit year to avoid dateutil using system current year

        # Case A: PM with explicit year
        # Note: now() must be AFTER the parsed date to avoid "future date" year adjustment logic
        with patch('option_auditor.parsers.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2023, 10, 16)
            mock_dt.strptime.side_effect = datetime.strptime

            # "10/15/2023 2:30 p" -> Oct 15 2023 14:30
            dt = self.tasty_parser._parse_tasty_datetime("10/15/2023 2:30 p")
            self.assertEqual(dt.year, 2023)
            self.assertEqual(dt.month, 10)
            self.assertEqual(dt.day, 15)
            self.assertEqual(dt.hour, 14)
            self.assertEqual(dt.minute, 30)

            # Case B: AM (Midnight logic usually 12a -> 00:00)
            # Use explicit year so dateutil behaves predictably
            dt_am = self.tasty_parser._parse_tasty_datetime("10/15/2023 12:00 a")
            self.assertEqual(dt_am.hour, 0)
            self.assertEqual(dt_am.minute, 0)

            # Case C: NOON (12:00 p) -> Should stay 12:00
            dt_noon = self.tasty_parser._parse_tasty_datetime("10/15/2023 12:00 p")
            self.assertEqual(dt_noon.hour, 12)

        # 2. Year Adjustment Logic
        # If dt > now + 2 days, subtract 1 year.
        # Scenario: Today is Jan 5, 2024. We parse a date that resolves to "12/31/2024".
        # We provide "12/31/2024" explicitly.
        # Since 2024-12-31 > 2024-01-07 (Now+2d), it should adjust to 2023.
        with patch('option_auditor.parsers.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 5)
            mock_dt.strptime.side_effect = datetime.strptime

            # We pass 2024 in string. dateutil parses as 2024.
            # Then logic checks: 2024-12-31 > 2024-01-07? Yes.
            # So it subtracts year -> 2023.
            dt_adj = self.tasty_parser._parse_tasty_datetime("12/31/2024 10:00 a")
            self.assertEqual(dt_adj.year, 2023)
            self.assertEqual(dt_adj.month, 12)
            self.assertEqual(dt_adj.day, 31)


    def test_sign_conventions(self):
        data = {
            "Time": ["2023-10-01 10:00"] * 6,
            "Underlying Symbol": ["SPY"] * 6,
            "Quantity": [1, 1, 1, 1, 1, 1],
            "Action": [
                "SELL_TO_OPEN",    # -1
                "BUY_TO_CLOSE",    # 1
                "EXERCISE",        # -1 (Close Long -> -1 qty usually in this parser logic? Wait, let's check code)
                                   # Code: sign = np.where(action.str.startswith("sell") | action.str.contains("exercise"), -1.0, 1.0)
                "ASSIGNMENT",      # 1
                "SELL_TO_CLOSE",   # -1
                "BUY_TO_OPEN"      # 1
            ],
            "Price": [1.0] * 6,
            "Commissions and Fees": [0.0] * 6,
            "Expiration Date": ["2023-10-20"] * 6,
            "Strike Price": [450] * 6,
            "Option Type": ["C"] * 6
        }
        df = pd.DataFrame(data)
        result = self.tasty_parser.parse(df)

        # SELL_TO_OPEN -> -1
        self.assertEqual(result.iloc[0]['qty'], -1.0)
        # BUY_TO_CLOSE -> 1
        self.assertEqual(result.iloc[1]['qty'], 1.0)
        # EXERCISE -> -1
        self.assertEqual(result.iloc[2]['qty'], -1.0)
        # ASSIGNMENT -> 1
        self.assertEqual(result.iloc[3]['qty'], 1.0)
        # SELL_TO_CLOSE -> -1
        self.assertEqual(result.iloc[4]['qty'], -1.0)
        # BUY_TO_OPEN -> 1
        self.assertEqual(result.iloc[5]['qty'], 1.0)


    def test_contract_id_generation(self):
        # Row 1: Stock (Option Type is NaN or Empty)
        # Row 2: Option
        data = {
            "Time": ["2023-10-01 10:00", "2023-10-01 10:00"],
            "Underlying Symbol": ["AAPL", "SPY"],
            "Quantity": [10, 1],
            "Action": ["BUY", "BUY_TO_OPEN"],
            "Price": [150.0, 2.5],
            "Commissions and Fees": [0.0, 0.0],
            "Expiration Date": [None, "2023-11-17"],
            "Strike Price": [None, 450.0],
            "Option Type": [None, "C"]
        }
        df = pd.DataFrame(data)

        result = self.tasty_parser.parse(df)

        # Row 1: Stock
        row1 = result.iloc[0]
        self.assertEqual(row1['asset_type'], 'STOCK')
        self.assertEqual(row1['contract_id'], "AAPL:::0.0")

        # Row 2: Option
        row2 = result.iloc[1]
        self.assertEqual(row2['asset_type'], 'OPT')
        # Format: SYMBOL:YYYY-MM-DD:RIGHT:STRIKE
        self.assertEqual(row2['contract_id'], "SPY:2023-11-17:C:450.0")

if __name__ == '__main__':
    unittest.main()
