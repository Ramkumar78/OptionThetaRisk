import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.parsers import TransactionParser, TastytradeParser, ManualInputParser, detect_broker

# Concrete class for testing abstract TransactionParser
class TestParser(TransactionParser):
    def parse(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

class TestParsersExtended:

    # 1. 'TransactionParser._parse_tasty_datetime'
    def test_parse_tasty_datetime_fallback_and_year_adjustment(self, mocker):
        parser = TestParser()

        # Mocking 'datetime' in 'option_auditor.parsers'
        mock_dt = mocker.patch("option_auditor.parsers.datetime")

        # Mocking 'dtparser' (dateutil) in 'option_auditor.parsers' to control what it returns
        mock_dtparser = mocker.patch("option_auditor.parsers.dtparser")

        # Configure 'strptime' to use the real datetime.strptime
        mock_dt.strptime.side_effect = datetime.strptime

        # --- Scenario A: Fallback Logic ---
        # We force dtparser to fail to ensure fallback logic is exercised.
        mock_dtparser.parse.side_effect = Exception("Force Fallback")

        # Set "now" to 2023-06-15
        mock_now = datetime(2023, 6, 15, 12, 0, 0)
        mock_dt.now.return_value = mock_now

        # Test input: "05/25 10:30p"
        # The code will try dtparser -> fail -> fallback.
        # Fallback logic: "05/25 10:30p" -> "2023/05/25 10:30"
        # Since 'p' is present, it adds 12 hours if not 12. 10:30 -> 22:30.
        # Note: We use 05/25 which is BEFORE now (06/15), so no year adjustment occurs.
        dt = parser._parse_tasty_datetime("05/25 10:30p")
        assert dt == pd.Timestamp("2023-05-25 22:30:00")

        # Test input: "05/25 10:30a"
        # Fallback logic: "05/25 10:30a" -> "2023/05/25 10:30"
        # 'p' not in string. 10:30 -> 10:30.
        dt_am = parser._parse_tasty_datetime("05/25 10:30a")
        assert dt_am == pd.Timestamp("2023-05-25 10:30:00")

        # --- Scenario B: Year Adjustment Logic ---
        # We test that if the parsed date is in the future, it is adjusted to previous year.
        # We use dtparser success path for this, as it is simpler to control via mock return_value.

        mock_dtparser.parse.side_effect = None # Stop raising exception

        # Set "now" to Jan 5, 2024
        mock_now_jan = datetime(2024, 1, 5, 12, 0, 0)
        mock_dt.now.return_value = mock_now_jan

        # Mock dtparser to return Dec 25, 2024 (which is > Jan 5 2024 + 2 days)
        mock_dtparser.parse.return_value = datetime(2024, 12, 25, 10, 0)

        # The actual string passed doesn't matter since we mocked parse()
        dt_adj = parser._parse_tasty_datetime("12/25 10:00am")

        # Expectation:
        # Parsed: 2024-12-25
        # Now+2d: 2024-01-07
        # Parsed > Now+2d -> Year adjusted to 2023
        assert dt_adj.year == 2023
        assert dt_adj.month == 12
        assert dt_adj.day == 25
        assert dt_adj.hour == 10

        # --- Scenario C: No Adjustment needed ---
        # Set "now" to Dec 20, 2024
        mock_now_dec = datetime(2024, 12, 20, 12, 0, 0)
        mock_dt.now.return_value = mock_now_dec

        # Mock dtparser to return Dec 25, 2024
        # Dec 25 is > Dec 20 + 2 (Dec 22). So it SHOULD adjust?
        # Wait, if I am in Dec 20, and date is Dec 25. That is future.
        # Yes, standard logic says if date is future > 2 days, assume it's previous year (maybe data error or wrap around?).
        # But usually we parse past dates.
        # Let's test a date in the past. Oct 25, 2024.

        mock_dtparser.parse.return_value = datetime(2024, 10, 25, 10, 0)
        dt_ok = parser._parse_tasty_datetime("10/25")

        assert dt_ok.year == 2024 # No change

        # --- Scenario D: Malformed string returns None ---
        mock_dtparser.parse.side_effect = Exception("Fail")
        mock_dt.strptime.side_effect = ValueError("Fail") # strptime fails

        assert parser._parse_tasty_datetime("invalid") is None


    # 2. 'TastytradeParser': Test 'parse' with missing columns
    def test_tasty_parser_missing_columns(self):
        parser = TastytradeParser()
        # Missing 'Action', 'Quantity', etc.
        df = pd.DataFrame({
            "Time": ["2023-01-01"],
            "Underlying Symbol": ["AAPL"]
        })

        # Should raise KeyError because required columns are missing
        with pytest.raises(KeyError, match="Tasty CSV missing"):
            parser.parse(df)

    # 3. 'ManualInputParser': Test 'parse' with mixed asset types
    def test_manual_parser_mixed_assets(self):
        parser = ManualInputParser()
        # Row 1: Stock (Action: Buy, No Right/Strike)
        # Row 2: Option (Action: Buy, Right: Call, Strike: 150)
        data = [
            {
                "date": "2023-01-01", "symbol": "AAPL", "action": "Buy", "qty": 10, "price": 150.0,
                "fees": 1.0, "expiry": "", "strike": "", "right": ""
            },
            {
                "date": "2023-01-01", "symbol": "AAPL", "action": "Buy", "qty": 1, "price": 5.0,
                "fees": 1.0, "expiry": "2023-02-17", "strike": 160.0, "right": "C"
            }
        ]
        df = pd.DataFrame(data)

        result = parser.parse(df)

        assert len(result) == 2

        # Check Stock Row (index 0)
        stock_row = result.iloc[0]
        assert stock_row["asset_type"] == "STOCK"
        assert stock_row["right"] == "" # Empty string, not NaN
        # Proceeds: -Qty * Price * Multiplier(1)
        # -10 * 150.0 * 1.0 = -1500.0
        assert stock_row["proceeds"] == -1500.0
        assert ":::0.0" in stock_row["contract_id"]

        # Check Option Row (index 1)
        opt_row = result.iloc[1]
        assert opt_row["asset_type"] == "OPT"
        assert opt_row["right"] == "C"
        # Proceeds: -Qty * Price * Multiplier(100)
        # -1 * 5.0 * 100.0 = -500.0
        assert opt_row["proceeds"] == -500.0
        assert ":C:160.0" in opt_row["contract_id"]

    # 4. 'detect_broker': Test detection logic
    def test_detect_broker_logic(self):
        # Tasty (by Underlying Symbol)
        df_tasty = pd.DataFrame(columns=["Underlying Symbol", "Action"])
        assert detect_broker(df_tasty) == "tasty"

        # Tasty (by Description + Symbol)
        df_tasty_2 = pd.DataFrame(columns=["Description", "Symbol"])
        assert detect_broker(df_tasty_2) == "tasty"

        # IBKR (by ClientAccountID)
        df_ibkr_1 = pd.DataFrame(columns=["ClientAccountID", "Symbol"])
        assert detect_broker(df_ibkr_1) == "ibkr"

        # IBKR (by Comm/Fee and T. Price)
        df_ibkr_2 = pd.DataFrame(columns=["Comm/Fee", "T. Price", "Quantity"])
        assert detect_broker(df_ibkr_2) == "ibkr"

        # Unknown / None
        df_unknown = pd.DataFrame(columns=["Random", "Columns"])
        assert detect_broker(df_unknown) is None
