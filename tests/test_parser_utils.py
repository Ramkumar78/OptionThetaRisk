import pandas as pd
import pytest
from option_auditor.parsers import ManualInputParser, detect_broker

class TestManualInputParser:
    def test_opt_column_mapping(self):
        """
        Test that 'opt' column is correctly mapped to 'right'.
        """
        parser = ManualInputParser()
        df = pd.DataFrame([
            {
                "date": "2023-10-01",
                "symbol": "SPY",
                "action": "BUY",
                "qty": 1,
                "price": 1.0,
                "fees": 0.5,
                "expiry": "2023-12-01",
                "strike": 400,
                "opt": "C"
            }
        ])
        result = parser.parse(df)
        assert "right" in result.columns
        assert result.iloc[0]["right"] == "C"
        assert result.iloc[0]["asset_type"] == "OPT"

    def test_shorthand_actions(self):
        """
        Test that shorthand actions 's' (sell) and 'b' (buy) are handled correctly.
        """
        parser = ManualInputParser()
        df = pd.DataFrame([
            {
                "date": "2023-10-01",
                "symbol": "AAPL",
                "action": "s",  # Shorthand for Sell
                "qty": 10,
                "price": 150.0,
                "fees": 1.0,
                "expiry": None,
                "strike": None,
                "opt": None
            },
            {
                "date": "2023-10-02",
                "symbol": "AAPL",
                "action": "b",  # Shorthand for Buy
                "qty": 5,
                "price": 155.0,
                "fees": 1.0,
                "expiry": None,
                "strike": None,
                "opt": None
            }
        ])
        result = parser.parse(df)

        # Check sell logic (should be negative qty)
        row_sell = result.iloc[0]
        assert row_sell["qty"] == -10.0

        # Check buy logic (should be positive qty)
        row_buy = result.iloc[1]
        assert row_buy["qty"] == 5.0

    def test_mixed_opt_types(self):
        """
        Test mixed 'opt' types (Call/Put vs Stock/None).
        """
        parser = ManualInputParser()
        df = pd.DataFrame([
            {
                "date": "2023-10-01",
                "symbol": "SPY",
                "action": "BUY",
                "qty": 1,
                "price": 1.0,
                "fees": 0.5,
                "expiry": "2023-12-01",
                "strike": 400,
                "opt": "P"
            },
            {
                "date": "2023-10-01",
                "symbol": "AMD",
                "action": "BUY",
                "qty": 100,
                "price": 100.0,
                "fees": 0.5,
                "expiry": None,
                "strike": None,
                "opt": "Stock" # Should not be mapped to C/P
            }
        ])
        result = parser.parse(df)

        assert result.iloc[0]["asset_type"] == "OPT"
        assert result.iloc[0]["right"] == "P"

        assert result.iloc[1]["asset_type"] == "STOCK"
        assert result.iloc[1]["right"] == ""


class TestBrokerDetection:
    def test_detect_tastytrade(self):
        """
        Test detection of Tastytrade format based on columns.
        """
        # Case 1: "Underlying Symbol" present
        df1 = pd.DataFrame(columns=["Underlying Symbol", "Time", "Date", "Call/Put"])
        assert detect_broker(df1) == "tasty"

        # Case 2: "Description" and "Symbol" present
        df2 = pd.DataFrame(columns=["Description", "Symbol", "Quantity", "Price"])
        assert detect_broker(df2) == "tasty"

    def test_detect_ibkr(self):
        """
        Test detection of IBKR format based on columns.
        """
        # Case 1: "ClientAccountID" present
        df1 = pd.DataFrame(columns=["ClientAccountID", "Symbol", "Currency"])
        assert detect_broker(df1) == "ibkr"

        # Case 2: "IBCommission" present
        df2 = pd.DataFrame(columns=["IBCommission", "Symbol", "TradeDate"])
        assert detect_broker(df2) == "ibkr"

        # Case 3: "Comm/Fee" and "T. Price" present
        df3 = pd.DataFrame(columns=["Comm/Fee", "T. Price", "Symbol", "Quantity"])
        assert detect_broker(df3) == "ibkr"

    def test_detect_unknown(self):
        """
        Test detection of unknown/unsupported format.
        """
        df = pd.DataFrame(columns=["RandomColumn", "AnotherColumn"])
        assert detect_broker(df) is None
