import pandas as pd
import pytest
from option_auditor.parsers import TransactionParser, TastytradeParser, TastytradeFillsParser
from datetime import datetime, timedelta

# Test abstract base class
def test_transaction_parser_abstract():
    with pytest.raises(TypeError):
        TransactionParser()

# Test TastytradeFillsParser custom logic (lines 85-86, 124, 132, 134, 137-145)
def test_tasty_fills_parser_edge_cases():
    parser = TastytradeFillsParser()

    # Test case for exception in total_money calculation (lines 85-86)
    # We add "dummy" to make it 6 tokens for fallback logic if needed

    df_fallback = pd.DataFrame([
        {
            # Hits line 134 (Call), 124 (30d), and date parsing
            "Description": "-1 Jan 20 30d 100 Call dummy",
            "Price": "1.00",
            "Time": "2025-01-01 10:00",
            "Symbol": "TEST",
            "Commissions": "0", "Fees": "0"
        },
        {
            # Hits line 132 (Put)
            "Description": "1 Jan 20 100 Put dummy",
            "Price": "1.00",
            "Time": "2025-01-01 10:00",
            "Symbol": "TEST",
            "Commissions": "0", "Fees": "0"
        },
        {
             # Invalid price to hit 85-86
            "Description": "-1 Jan 20 100 Call dummy",
            "Price": "Free",
            "Time": "2025-01-01 10:00",
            "Symbol": "TEST",
            "Commissions": "0", "Fees": "0"
        }
    ])

    res = parser.parse(df_fallback)
    assert len(res) >= 3 # Now all should pass

    # Check if Invalid price resulted in 0 proceeds (for the third item)
    # The third item is a short call (-1). Proceeds = -(-1) * 0 * 100 = 0.0
    row_invalid_price = res[(res['right'] == 'C') & (res['proceeds'] == 0.0)]
    assert not row_invalid_price.empty

    # Test lines 140-141: Year rollover logic in fallback
    # If ts.month > 10 and month_num < 3 -> year + 1
    df_rollover = pd.DataFrame([{
        "Description": "-1 Jan 20 100 Call dummy",
        "Price": "1.00",
        "Time": "2023-12-01 10:00", # Dec -> month > 10
        "Symbol": "TEST",
        "Commissions": "0", "Fees": "0"
    }])

    res_rollover = parser.parse(df_rollover)
    assert len(res_rollover) > 0
    # Expiry year should be 2024 (2023 + 1) because Jan is < 3
    assert res_rollover.iloc[0]['expiry'].year == 2024


class MockParser(TransactionParser):
    def parse(self, df):
        return df

def test_parse_tasty_datetime_methods():
    parser = MockParser()

    # Test _parse_tasty_datetime custom logic (lines 28-32)
    # We use "p" or "a" with spaces to confuse dateutil.parser but satisfy custom logic

    res = parser._parse_tasty_datetime("02/20 02:00 p")
    # If dtparser fails, it goes to custom.
    # custom: s="02/20 02:00", is_pm=True. parts=["02/20", "02:00"].
    # dt = 2025/02/20 02:00.
    # is_pm and 2 != 12 -> add 12 -> 14:00.

    assert res is not None
    assert res.hour == 14

    # To hit line 31 (12 AM case):
    # "02/20 12:00 a"
    res_am = parser._parse_tasty_datetime("02/20 12:00 a")
    # custom: is_pm=False. dt=12:00. not is_pm and 12==12 -> sub 12 -> 00:00.

    assert res_am is not None
    assert res_am.hour == 0
