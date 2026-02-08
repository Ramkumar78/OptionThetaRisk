import pytest
import pandas as pd
import numpy as np
from option_auditor.parsers import TastytradeParser

class TestTastytradeParser:
    @pytest.fixture
    def parser(self):
        return TastytradeParser()

    def test_sign_assignment(self, parser):
        # Test Buy, Sell, Assignment, Exercise
        data = {
            "Time": ["2023-01-01 10:00"] * 4,
            "Underlying Symbol": ["AAPL"] * 4,
            "Quantity": ["1", "1", "1", "1"],
            "Action": ["Buy to Open", "Sell to Open", "Assignment", "Exercise"],
            "Price": ["1.0"] * 4,
            "Commissions and Fees": ["0.0"] * 4,
            "Expiration Date": ["2023-02-01"] * 4,
            "Strike Price": ["150"] * 4,
            "Option Type": ["C"] * 4
        }
        df = pd.DataFrame(data)
        out = parser.parse(df)

        # Buy -> 1.0 (positive)
        assert out.iloc[0]["qty"] == 1.0
        # Sell -> -1.0 (negative)
        assert out.iloc[1]["qty"] == -1.0
        # Assignment -> 1.0 (positive)
        assert out.iloc[2]["qty"] == 1.0
        # Exercise -> -1.0 (negative)
        assert out.iloc[3]["qty"] == -1.0

    def test_multiplier_logic(self, parser):
        # Test Stock (multiplier 1) and Option (multiplier 100)
        data = {
            "Time": ["2023-01-01 10:00"] * 2,
            "Underlying Symbol": ["AAPL", "AAPL"],
            "Quantity": ["10", "1"],
            "Action": ["Buy", "Buy"],
            "Price": ["150.0", "5.0"],
            "Commissions and Fees": ["0.0", "0.0"],
            "Expiration Date": [None, "2023-02-01"],
            "Strike Price": [None, "150"],
            "Option Type": [None, "C"] # None -> Stock, "C" -> Option
        }
        df = pd.DataFrame(data)
        out = parser.parse(df)

        # Stock: qty=10, price=150, multiplier=1
        # proceeds = -qty * price * multiplier = -10 * 150 * 1 = -1500
        stock_row = out.iloc[0]
        assert stock_row["asset_type"] == "STOCK"
        assert stock_row["proceeds"] == -1500.0

        # Option: qty=1, price=5, multiplier=100
        # proceeds = -1 * 5 * 100 = -500
        opt_row = out.iloc[1]
        assert opt_row["asset_type"] == "OPT"
        assert opt_row["proceeds"] == -500.0

    def test_contract_id_generation(self, parser):
        data = {
            "Time": ["2023-01-01 10:00"] * 2,
            "Underlying Symbol": ["AAPL", "GOOG"],
            "Quantity": ["1", "1"],
            "Action": ["Buy", "Buy"],
            "Price": ["1.0", "1.0"],
            "Commissions and Fees": ["0.0", "0.0"],
            "Expiration Date": [None, "2023-02-17"],
            "Strike Price": [None, "150.5"],
            "Option Type": [None, "P"]
        }
        df = pd.DataFrame(data)
        out = parser.parse(df)

        # Stock: SYMBOL:::0.0
        assert out.iloc[0]["contract_id"] == "AAPL:::0.0"

        # Option: SYMBOL:EXP:RIGHT:STRIKE
        # 2023-02-17
        # Note: round(strike, 4) means 150.5 stays 150.5
        assert out.iloc[1]["contract_id"] == "GOOG:2023-02-17:P:150.5"

    def test_missing_columns_error(self, parser):
        df = pd.DataFrame({"Time": ["2023-01-01"]})
        # Should raise KeyError because columns like "Underlying Symbol" are missing
        with pytest.raises(KeyError, match="Tasty CSV missing"):
            parser.parse(df)
