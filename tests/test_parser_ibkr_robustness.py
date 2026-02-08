import pytest
import pandas as pd
from option_auditor.parsers import IBKRParser

class TestIBKRParserRobustness:
    """
    Tests for IBKRParser robustness, covering various column formats, asset classes, and data variations.
    """

    def test_column_header_variations(self):
        """
        Test that the parser correctly handles variations in column headers for Price and Fees.
        """
        parser = IBKRParser()

        # Scenario 1: 'T. Price' and 'Comm/Fee'
        df1 = pd.DataFrame([{
            "Symbol": "AAPL",
            "DateTime": "2023-10-26 10:00:00",
            "Quantity": 10,
            "T. Price": 150.0,
            "Comm/Fee": -1.0
        }])
        res1 = parser.parse(df1)
        assert not res1.empty
        assert res1.iloc[0]["symbol"] == "AAPL"
        assert res1.iloc[0]["qty"] == 10.0
        # Proceeds calculation check: -Qty * Price * Multiplier (1 for stock)
        # Note: proceeds_col is not present, so fallback calculation is used.
        expected_proceeds1 = -10.0 * 150.0 * 1.0
        assert res1.iloc[0]["proceeds"] == expected_proceeds1
        assert res1.iloc[0]["fees"] == 1.0

        # Scenario 2: 'TradePrice' and 'Commission'
        df2 = pd.DataFrame([{
            "UnderlyingSymbol": "MSFT",
            "Date/Time": "2023-10-27 11:00:00",
            "Qty": 5,
            "TradePrice": 300.0,
            "Commission": 2.5
        }])
        res2 = parser.parse(df2)
        assert not res2.empty
        assert res2.iloc[0]["symbol"] == "MSFT"
        assert res2.iloc[0]["qty"] == 5.0
        expected_proceeds2 = -5.0 * 300.0 * 1.0
        assert res2.iloc[0]["proceeds"] == expected_proceeds2
        assert res2.iloc[0]["fees"] == 2.5

        # Scenario 3: 'Price' and 'IBCommission'
        df3 = pd.DataFrame([{
            "Symbol": "GOOG",
            "TradeDate": "2023-10-28 12:00:00",
            "Quantity": 20,
            "Price": 100.0,
            "IBCommission": 0.5
        }])
        res3 = parser.parse(df3)
        assert not res3.empty
        assert res3.iloc[0]["symbol"] == "GOOG"
        expected_proceeds3 = -20.0 * 100.0 * 1.0
        assert res3.iloc[0]["proceeds"] == expected_proceeds3
        assert res3.iloc[0]["fees"] == 0.5

    def test_asset_class_parsing_stk(self):
        """
        Test parsing of Stock asset class using explicit 'AssetClass' column values.
        """
        parser = IBKRParser()

        # Test explicit 'STK', 'EQUITY', 'STOCK'
        variations = ["STK", "EQUITY", "STOCK"]

        for variant in variations:
            df = pd.DataFrame([{
                "Symbol": "AAPL",
                "DateTime": "2023-10-26 10:00:00",
                "Quantity": 100,
                "T. Price": 150.0,
                "AssetClass": variant
            }])
            res = parser.parse(df)
            assert res.iloc[0]["asset_type"] == "STOCK"
            assert res.iloc[0]["contract_id"] == "AAPL:::0.0"

    def test_asset_class_parsing_opt(self):
        """
        Test parsing of Option asset class, both explicit and inferred.
        """
        parser = IBKRParser()

        # Case 1: Explicit 'OPT' asset class
        df_explicit = pd.DataFrame([{
            "Symbol": "AAPL",
            "DateTime": "2023-10-26 10:00:00",
            "Quantity": 1,
            "T. Price": 5.0,
            "AssetClass": "OPT",
            "Expiry": "2023-11-17",
            "Strike": 155.0,
            "Put/Call": "C"
        }])
        res_explicit = parser.parse(df_explicit)
        assert res_explicit.iloc[0]["asset_type"] == "OPT"
        assert res_explicit.iloc[0]["contract_id"] == "AAPL:2023-11-17:C:155.0"
        # Multiplier check: 100 for OPT
        expected_proceeds = -1.0 * 5.0 * 100.0
        assert res_explicit.iloc[0]["proceeds"] == expected_proceeds

        # Case 2: Inferred from 'Put/Call' column (no AssetClass column)
        df_inferred = pd.DataFrame([{
            "Symbol": "MSFT",
            "DateTime": "2023-10-27 11:00:00",
            "Quantity": 1,
            "T. Price": 2.5,
            # No AssetClass
            "ExpirationDate": "2023-12-15",
            "StrikePrice": 310.0,
            "C/P": "P"
        }])
        res_inferred = parser.parse(df_inferred)
        assert res_inferred.iloc[0]["asset_type"] == "OPT"
        assert res_inferred.iloc[0]["contract_id"] == "MSFT:2023-12-15:P:310.0"

    def test_parse_ib_dt_semicolon(self):
        """
        Test the _parse_ib_dt helper with semi-colon delimited date strings.
        """
        parser = IBKRParser()

        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "20231026;153000", # Specific format to test
            "Quantity": 10,
            "T. Price": 150.0
        }])

        res = parser.parse(df)
        assert not res.empty
        expected_dt = pd.Timestamp("2023-10-26 15:30:00")
        assert res.iloc[0]["datetime"] == expected_dt

    def test_mixed_portfolio(self):
        """
        Test parsing a mixed DataFrame containing both Stock and Option rows.
        """
        parser = IBKRParser()

        data = [
            # Stock Row
            {
                "Symbol": "AAPL",
                "DateTime": "2023-10-26 10:00:00",
                "Quantity": 100,
                "T. Price": 150.0,
                "AssetClass": "STK",
                "Comm/Fee": -1.0
            },
            # Option Row
            {
                "Symbol": "AAPL",
                "DateTime": "2023-10-26 10:05:00",
                "Quantity": -1,
                "T. Price": 2.0,
                "AssetClass": "OPT",
                "Expiry": "2023-11-17",
                "Strike": 160.0,
                "Put/Call": "C",
                "Comm/Fee": -0.65
            }
        ]
        df = pd.DataFrame(data)

        res = parser.parse(df)
        assert len(res) == 2

        # Verify Stock Row
        row_stk = res.iloc[0]
        assert row_stk["asset_type"] == "STOCK"
        assert row_stk["symbol"] == "AAPL"
        assert row_stk["qty"] == 100.0

        # Verify Option Row
        row_opt = res.iloc[1]
        assert row_opt["asset_type"] == "OPT"
        assert row_opt["symbol"] == "AAPL"
        assert row_opt["qty"] == -1.0
        assert row_opt["contract_id"] == "AAPL:2023-11-17:C:160.0"
