import pytest
import pandas as pd
import numpy as np
from option_auditor.parsers import IBKRParser

class TestIBKRParserDetection:
    """
    Test suite focused on maximizing coverage for IBKRParser detection logic:
    - find_col helper
    - _parse_ib_dt helper
    - Zero quantity filtering
    """

    def setup_method(self):
        self.parser = IBKRParser()

    # --- find_col Tests ---

    def test_find_col_case_insensitivity(self):
        """Test that find_col handles mixed case column names."""
        df = pd.DataFrame([{
            "sYmBoL": "AAPL",
            "dAtE/tImE": "2023-10-27 10:00:00",
            "qUaNtItY": 100
        }])
        result = self.parser.parse(df)
        assert not result.empty
        assert result.iloc[0]["symbol"] == "AAPL"
        assert result.iloc[0]["qty"] == 100

    def test_find_col_whitespace_handling(self):
        """Test that find_col handles leading/trailing whitespace."""
        df = pd.DataFrame([{
            " Symbol ": "MSFT",
            " Date/Time ": "2023-10-27 10:00:00",
            " Quantity ": 50
        }])
        result = self.parser.parse(df)
        assert not result.empty
        assert result.iloc[0]["symbol"] == "MSFT"
        assert result.iloc[0]["qty"] == 50

    def test_find_col_variations_priority(self):
        """Test that find_col prioritizes columns correctly based on candidate list order."""
        # Symbol candidates: ["Symbol", "UnderlyingSymbol"]

        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "UnderlyingSymbol": "MSFT", # Should be ignored if Symbol is found
            "Date/Time": "2023-10-27 10:00:00",
            "Quantity": 100
        }])
        result = self.parser.parse(df)
        assert result.iloc[0]["symbol"] == "AAPL"

        # Now test the reverse: Only UnderlyingSymbol exists
        df2 = pd.DataFrame([{
            "UnderlyingSymbol": "GOOG",
            "Date/Time": "2023-10-27 10:00:00",
            "Quantity": 100
        }])
        result2 = self.parser.parse(df2)
        assert result2.iloc[0]["symbol"] == "GOOG"

    def test_missing_mandatory_columns(self):
        """Test that KeyError is raised when mandatory columns are missing."""
        # Missing Symbol
        df_no_sym = pd.DataFrame([{"Date/Time": "2023-10-27", "Quantity": 10}])
        with pytest.raises(KeyError, match="Missing Symbol column"):
            self.parser.parse(df_no_sym)

        # Missing Date
        df_no_date = pd.DataFrame([{"Symbol": "AAPL", "Quantity": 10}])
        with pytest.raises(KeyError, match="Missing Date column"):
            self.parser.parse(df_no_date)

        # Missing Quantity
        df_no_qty = pd.DataFrame([{"Symbol": "AAPL", "Date/Time": "2023-10-27"}])
        with pytest.raises(KeyError, match="Missing Quantity column"):
            self.parser.parse(df_no_qty)

    # --- _parse_ib_dt Tests ---

    def test_parse_ib_dt_semicolon_format(self):
        """Test parsing of IBKR Flex Query semicolon format (YYYYMMDD;HHMMSS)."""
        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "20231027;153000",
            "Quantity": 10
        }])
        result = self.parser.parse(df)
        assert result.iloc[0]["datetime"] == pd.Timestamp("2023-10-27 15:30:00")

    def test_parse_ib_dt_semicolon_variations(self):
        """Test parsing of semicolon format with separators (YYYY-MM-DD;HH:MM:SS)."""
        # The code does replace("-", "") and replace(":", "") before strptime
        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "2023-10-27;15:30:00",
            "Quantity": 10
        }])
        result = self.parser.parse(df)
        assert result.iloc[0]["datetime"] == pd.Timestamp("2023-10-27 15:30:00")

    def test_parse_ib_dt_standard_formats(self):
        """Test parsing of standard dateutil formats."""
        df = pd.DataFrame([
            {"Symbol": "A", "Date/Time": "2023-10-27 10:00:00", "Quantity": 1},
            {"Symbol": "B", "Date/Time": "10/27/2023 10:00 AM", "Quantity": 1},
            {"Symbol": "C", "Date/Time": "2023-10-27T10:00:00", "Quantity": 1}
        ])
        result = self.parser.parse(df)
        assert all(result["datetime"] == pd.Timestamp("2023-10-27 10:00:00"))

    def test_parse_ib_dt_invalid_dates(self):
        """Test that invalid dates result in NaT."""
        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "InvalidDate",
            "Quantity": 10
        }])
        result = self.parser.parse(df)
        assert pd.isna(result.iloc[0]["datetime"])

    def test_parse_ib_dt_empty(self):
        """Test that empty/null dates result in NaT."""
        df = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": "",
            "Quantity": 10
        }])
        result = self.parser.parse(df)
        assert pd.isna(result.iloc[0]["datetime"])

        df_nan = pd.DataFrame([{
            "Symbol": "AAPL",
            "Date/Time": np.nan,
            "Quantity": 10
        }])
        result_nan = self.parser.parse(df_nan)
        assert pd.isna(result_nan.iloc[0]["datetime"])


    # --- Zero Quantity Filtering Tests ---

    def test_filter_zero_quantity_int(self):
        """Test filtering of integer 0 quantity."""
        df = pd.DataFrame([
            {"Symbol": "A", "Date/Time": "2023-10-27", "Quantity": 10},
            {"Symbol": "B", "Date/Time": "2023-10-27", "Quantity": 0},
            {"Symbol": "C", "Date/Time": "2023-10-27", "Quantity": -10}
        ])
        result = self.parser.parse(df)
        assert len(result) == 2
        assert "B" not in result["symbol"].values
        assert "A" in result["symbol"].values
        assert "C" in result["symbol"].values

    def test_filter_zero_quantity_float(self):
        """Test filtering of float 0.0 quantity."""
        df = pd.DataFrame([
            {"Symbol": "A", "Date/Time": "2023-10-27", "Quantity": 10.5},
            {"Symbol": "B", "Date/Time": "2023-10-27", "Quantity": 0.0},
            {"Symbol": "C", "Date/Time": "2023-10-27", "Quantity": -0.0} # Should be 0
        ])
        result = self.parser.parse(df)
        assert len(result) == 1
        assert "A" in result["symbol"].values
        assert "B" not in result["symbol"].values

    def test_filter_zero_quantity_string(self):
        """Test filtering of string "0" quantity."""
        df = pd.DataFrame([
            {"Symbol": "A", "Date/Time": "2023-10-27", "Quantity": "10"},
            {"Symbol": "B", "Date/Time": "2023-10-27", "Quantity": "0"},
            {"Symbol": "C", "Date/Time": "2023-10-27", "Quantity": "0.0"}
        ])
        result = self.parser.parse(df)
        assert len(result) == 1
        assert "A" in result["symbol"].values

    def test_filter_nan_quantity(self):
        """Test that NaN/None quantity defaults to 0 and is filtered."""
        df = pd.DataFrame([
            {"Symbol": "A", "Date/Time": "2023-10-27", "Quantity": 10},
            {"Symbol": "B", "Date/Time": "2023-10-27", "Quantity": np.nan},
            {"Symbol": "C", "Date/Time": "2023-10-27", "Quantity": None}
        ])
        result = self.parser.parse(df)
        assert len(result) == 1
        assert "A" in result["symbol"].values
