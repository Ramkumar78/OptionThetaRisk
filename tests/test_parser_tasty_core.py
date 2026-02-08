import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from option_auditor.parsers import TastytradeParser

class TestTastytradeParserCore:
    @pytest.fixture
    def parser(self):
        return TastytradeParser()

    def _create_mock_df(self, data):
        # Helper to create a DataFrame with required columns, filling defaults
        default_columns = [
            "Time", "Underlying Symbol", "Quantity", "Action", "Price",
            "Commissions and Fees", "Expiration Date", "Strike Price", "Option Type"
        ]

        # Start with defaults
        base_data = {
            "Time": ["2023-01-01 12:00:00"] * len(data.get("Action", [])),
            "Underlying Symbol": ["SPY"] * len(data.get("Action", [])),
            "Quantity": ["1"] * len(data.get("Action", [])),
            "Action": ["Buy to Open"] * len(data.get("Action", [])),
            "Price": ["100.0"] * len(data.get("Action", [])),
            "Commissions and Fees": ["0.0"] * len(data.get("Action", [])),
            "Expiration Date": [""] * len(data.get("Action", [])),
            "Strike Price": [""] * len(data.get("Action", [])),
            "Option Type": [""] * len(data.get("Action", []))
        }

        # Override with provided data
        # Ensure length matches if data is provided as lists
        rows = max(len(v) for v in data.values()) if data else 1

        # Expand base data to match rows
        expanded_base = {k: [v[0]] * rows for k, v in base_data.items()}

        # Update with input data
        expanded_base.update(data)

        return pd.DataFrame(expanded_base)

    def test_action_signs_comprehensive(self, parser):
        """Test 1: Logic converting 'Sell' actions to negative quantities."""
        actions = [
            "Sell to Open", "Sell to Close", "sell to open", "SELL TO CLOSE", # Sell variants
            "Exercise", "exercise", # Exercise variants
            "Buy to Open", "Buy to Close", "Assignment", "assignment", # Buy variants
            "Unknown Action" # Should default to positive
        ]

        data = {
            "Action": actions,
            "Quantity": ["1"] * len(actions)
        }

        df = self._create_mock_df(data)
        result = parser.parse(df)

        # Expected signs:
        # Sell/Exercise -> -1.0
        # Buy/Assignment/Unknown -> 1.0

        expected_signs = [
            -1.0, -1.0, -1.0, -1.0, # Sell
            -1.0, -1.0,             # Exercise
            1.0, 1.0, 1.0, 1.0,     # Buy
            1.0                     # Unknown
        ]

        # Result qty should be Quantity * Sign
        # Quantity is 1, so result should be equal to sign
        np.testing.assert_array_equal(result["qty"].values, expected_signs)

    def test_asset_type_and_multiplier_logic(self, parser):
        """Test 2: Multiplier logic distinguishing between STOCK (1.0) and OPT (100.0)."""
        # Option Types that should be STOCK
        stock_types = [np.nan, None, "", "  ", "nan", "NaN"]
        # Option Types that should be OPT
        opt_types = ["C", "P", " C ", "Call", "PUT"]

        option_types = stock_types + opt_types
        count = len(option_types)

        data = {
            "Option Type": option_types,
            "Action": ["Buy"] * count, # Use Buy so sign is positive
            "Quantity": ["1"] * count,
            "Price": ["10.0"] * count,
            # Need expiry/strike/right for OPT to be valid rows generally, but parser calculates proceeds before filtering?
            # Looking at code: Proceeds calculated before filtering. But invalid rows are filtered out at the end.
            # However, the user wants to test multiplier logic.
            # Wait, `TastytradeParser.parse` filters invalid rows at the end:
            # `out = out[is_valid_opt | is_valid_stock].copy()`
            # So I need to provide valid data for OPT rows so they are not dropped.
            "Expiration Date": [""] * len(stock_types) + ["2023-12-01"] * len(opt_types),
            "Strike Price": [""] * len(stock_types) + ["100"] * len(opt_types),
            "Underlying Symbol": ["SPY"] * count
        }

        df = self._create_mock_df(data)

        # For the OPT rows, we need to make sure "Option Type" is clean enough for "right" extraction?
        # Code: `out["right"] = opt_type.str[0]`
        # If "Option Type" is "Call", right is "C".
        # If "Option Type" is "PUT", right is "P".
        # If "Option Type" is " C ", right is "C" (after strip).

        result = parser.parse(df)

        # Verify count.
        # Stock types should be kept (is_valid_stock relies on asset_type == "STOCK").
        # Opt types should be kept (is_valid_opt relies on asset_type == "OPT" & expiry & right in [C, P]).
        # "Call" -> right="C", valid.
        # "PUT" -> right="P", valid.

        assert len(result) == count

        # Verify Asset Types
        assert all(result.iloc[:len(stock_types)]["asset_type"] == "STOCK")
        assert all(result.iloc[len(stock_types):]["asset_type"] == "OPT")

        # Verify Multipliers / Proceeds
        # Proceeds = -qty * price * multiplier
        # Qty=1, Price=10.
        # Stock: -1 * 10 * 1 = -10.0
        # Opt: -1 * 10 * 100 = -1000.0

        expected_proceeds_stock = -10.0
        expected_proceeds_opt = -1000.0

        np.testing.assert_array_almost_equal(
            result.iloc[:len(stock_types)]["proceeds"].values,
            [expected_proceeds_stock] * len(stock_types)
        )

        np.testing.assert_array_almost_equal(
            result.iloc[len(stock_types):]["proceeds"].values,
            [expected_proceeds_opt] * len(opt_types)
        )

    def test_contract_id_formatting_details(self, parser):
        """Test 3: Contract_id string formatting for options vs stocks."""
        data = {
            "Action": ["Buy", "Buy", "Buy"],
            "Option Type": ["", "C", "P"], # Stock, Opt, Opt
            "Underlying Symbol": ["AAPL", "SPY", "IWM"],
            "Expiration Date": ["", "2023-12-01", "2024-01-15"],
            "Strike Price": ["", "450", "190.5"],
            "Quantity": ["1", "1", "1"],
            "Price": ["10", "5", "2"]
        }

        df = self._create_mock_df(data)
        result = parser.parse(df)

        # 1. Stock
        # "AAPL" -> "AAPL:::0.0"
        row0 = result.iloc[0]
        assert row0["symbol"] == "AAPL"
        assert row0["asset_type"] == "STOCK"
        assert row0["contract_id"] == "AAPL:::0.0"

        # 2. Option 1
        # "SPY", "2023-12-01", "C", "450" -> "SPY:2023-12-01:C:450.0"
        row1 = result.iloc[1]
        assert row1["symbol"] == "SPY"
        assert row1["asset_type"] == "OPT"
        assert row1["contract_id"] == "SPY:2023-12-01:C:450.0"

        # 3. Option 2 (Float Strike)
        # "IWM", "2024-01-15", "P", "190.5" -> "IWM:2024-01-15:P:190.5"
        row2 = result.iloc[2]
        assert row2["symbol"] == "IWM"
        assert row2["asset_type"] == "OPT"
        assert row2["contract_id"] == "IWM:2024-01-15:P:190.5"
