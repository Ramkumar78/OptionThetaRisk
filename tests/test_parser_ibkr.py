import pytest
import pandas as pd
from option_auditor.parsers import IBKRParser

class TestIBKRParser:

    def test_find_col_variations(self):
        """
        Test that the parser correctly identifies columns regardless of variations in headers.
        """
        variations = [
            {
                "cols": {
                    "sym": "Symbol",
                    "date": "Date/Time",
                    "qty": "Quantity",
                    "price": "T. Price"
                },
                "data": ["AAPL", "2023-10-26 10:00:00", 100, 150.0]
            },
            {
                "cols": {
                    "sym": "UnderlyingSymbol",
                    "date": "DateTime",
                    "qty": "Qty",
                    "price": "TradePrice"
                },
                "data": ["MSFT", "2023-10-27 11:00:00", 50, 300.0]
            },
             {
                "cols": {
                    "sym": "Symbol",
                    "date": "TradeDate",
                    "qty": "Quantity",
                    "price": "Price"
                },
                "data": ["GOOG", "2023-10-28 12:00:00", 25, 2000.0]
            }
        ]

        parser = IBKRParser()

        for case in variations:
            cols_map = case["cols"]
            data = case["data"]

            # Construct DataFrame with specific column names
            df = pd.DataFrame([{
                cols_map["sym"]: data[0],
                cols_map["date"]: data[1],
                cols_map["qty"]: data[2],
                cols_map["price"]: data[3]
            }])

            result = parser.parse(df)

            assert not result.empty
            assert result.iloc[0]["symbol"] == data[0]
            assert result.iloc[0]["qty"] == float(data[2])
            # Price is used to calculate proceeds if Proceeds column is missing
            # Proceeds = -Qty * Price * Multiplier (1 for stock)
            expected_proceeds = -float(data[2]) * float(data[3])
            assert result.iloc[0]["proceeds"] == expected_proceeds


    def test_parse_ib_dt_formats(self):
        """
        Test that the parser handles both standard and semicolon-separated date formats.
        """
        parser = IBKRParser()

        # Case 1: Standard Format
        df_standard = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "2023-10-26 15:30:00",
            "Quantity": 10
        }])
        res_standard = parser.parse(df_standard)
        assert res_standard.iloc[0]["datetime"] == pd.Timestamp("2023-10-26 15:30:00")

        # Case 2: Semicolon Format (IBKR Flex Query often uses this)
        df_semicolon = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "20231026;153000",
            "Quantity": 10
        }])
        res_semicolon = parser.parse(df_semicolon)
        assert res_semicolon.iloc[0]["datetime"] == pd.Timestamp("2023-10-26 15:30:00")

        # Case 3: Mixed / Invalid (Should result in NaT or failure, handled gracefully?)
        # Let's test a mixed case just to be sure
        df_mixed = pd.DataFrame([
            {"Symbol": "AAPL", "Date/Time": "2023-10-26 15:30:00", "Quantity": 10},
            {"Symbol": "MSFT", "Date/Time": "20231027;093000", "Quantity": 5}
        ])
        res_mixed = parser.parse(df_mixed)
        assert res_mixed.iloc[0]["datetime"] == pd.Timestamp("2023-10-26 15:30:00")
        assert res_mixed.iloc[1]["datetime"] == pd.Timestamp("2023-10-27 09:30:00")


    def test_filter_zero_quantity(self):
        """
        Test that rows with zero quantity are filtered out.
        """
        parser = IBKRParser()

        df = pd.DataFrame([
            {"Symbol": "AAPL", "Date/Time": "2023-10-26 10:00:00", "Quantity": 100},
            {"Symbol": "MSFT", "Date/Time": "2023-10-26 10:00:00", "Quantity": 0},  # Should be filtered
            {"Symbol": "GOOG", "Date/Time": "2023-10-26 10:00:00", "Quantity": -50}
        ])

        result = parser.parse(df)

        assert len(result) == 2
        symbols = result["symbol"].tolist()
        assert "AAPL" in symbols
        assert "GOOG" in symbols
        assert "MSFT" not in symbols
