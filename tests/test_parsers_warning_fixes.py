import pytest
import pandas as pd
import numpy as np
from option_auditor.parsers import TastytradeParser, IBKRParser, ManualInputParser

class TestParsersWarningFixes:
    """
    Tests specifically targeting the fix for pandas FutureWarning regarding
    incompatible dtype assignments (cleaning 'right' column).
    """

    def test_tasty_parser_nan_option_type(self):
        """
        Test that TastytradeParser handles NaN in 'Option Type' correctly
        without raising FutureWarning (implicit check) and producing correct output.
        """
        parser = TastytradeParser()
        df = pd.DataFrame({
            "Time": ["2023-10-25 10:00", "2023-10-25 10:00"],
            "Underlying Symbol": ["AAPL", "GOOG"],
            "Quantity": ["100", "1"],
            "Action": ["Buy", "Buy"],
            "Price": ["150.0", "5.0"],
            "Commissions and Fees": ["0.0", "1.0"],
            "Expiration Date": [None, "2023-11-17"],
            "Strike Price": [None, "150"],
            "Option Type": [np.nan, "Call"] # One stock (NaN), one Option
        })

        # Process
        out = parser.parse(df)

        # Assertions
        assert len(out) == 2
        
        # Check Stock Row
        stock_row = out[out["asset_type"] == "STOCK"].iloc[0]
        assert stock_row["right"] == "" 
        # Check dtype of 'right' column
        assert out["right"].dtype == "O" # Object type

        # Check Option Row
        opt_row = out[out["asset_type"] == "OPT"].iloc[0]
        assert opt_row["right"] == "C"

    def test_ibkr_parser_missing_right_column(self):
        """
        Test detection of stock when 'Put/Call' column is missing or full of NaNs.
        """
        parser = IBKRParser()
        # DataFrame without "Put/Call" column (simulating stock-only export or missing col)
        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "2023-10-25 10:00:00",
            "Quantity": "100",
            "T. Price": "150.00",
            "Comm/Fee": "1.0"
        }])

        out = parser.parse(df)

        assert len(out) == 1
        assert out.iloc[0]["asset_type"] == "STOCK"
        assert out.iloc[0]["right"] == ""
        assert out["right"].dtype == "O"

    def test_manual_parser_mixed_types(self):
        """
        Test ManualInputParser with mixed Stock and Option inputs causing NaN in 'right'.
        """
        parser = ManualInputParser()
        df = pd.DataFrame([
            {
                "date": "2023-10-25",
                "symbol": "AAPL",
                "action": "Buy",
                "qty": 100,
                "price": 150,
                "fees": 0,
                "expiry": None,
                "strike": None,
                "right": None # Stock
            },
            {
                "date": "2023-10-25",
                "symbol": "GOOG",
                "action": "Buy",
                "qty": 1,
                "price": 5.0,
                "fees": 0,
                "expiry": "2023-11-17",
                "strike": 150,
                "right": "C" # Option
            }
        ])

        out = parser.parse(df)

        assert len(out) == 2
        assert out.iloc[0]["asset_type"] == "STOCK"
        assert out.iloc[0]["right"] == ""
        
        assert out.iloc[1]["asset_type"] == "OPT"
        assert out.iloc[1]["right"] == "C"
        
        # Critical check: Ensure column is object, not float (if it were float, strings would fail or warn)
        assert out["right"].dtype == "O"
