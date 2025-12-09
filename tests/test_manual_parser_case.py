import pandas as pd
from option_auditor.parsers import ManualInputParser
import pytest

def test_manual_input_lowercase_keys():
    # Simulate data coming from frontend (usually lowercase keys if JSON)
    # But wait, frontend sends FormData, which we parse into a list of dicts.
    # The list of dicts keys come from frontend state variable names?
    # In webapp/app.py: manual_data = [row for row in manual_data ...]
    # The frontend code Audit.tsx state: manualRows have keys: id, date, symbol, action, qty, price, expiry, strike, opt
    # Ah! 'opt' instead of 'right' or 'type'.

    # Let's check Audit.tsx again for 'opt'
    # <select value={row.opt} ...> <option>Call</option><option>Put</option><option>Stock</option>

    # So the key is 'opt'.
    # ManualInputParser expects 'right'.
    # This is likely the bug causing mismatches or errors.

    data = [{
        "date": "2023-10-01",
        "symbol": "SPY",
        "action": "STO",
        "qty": 1,
        "price": 5.0,
        "fees": 1.0,
        "expiry": "2023-12-01",
        "strike": 400,
        "opt": "Put" # Frontend sends 'opt'
    }]

    # ManualInputParser checks required = ["date", ..., "right"]
    # It will fail or fill None for "right".

    df = pd.DataFrame(data)
    parser = ManualInputParser()

    # This should handle "opt" -> "right" mapping if implemented, or fail.
    try:
        res = parser.parse(df)
        print("Columns:", res.columns)
        print(res.iloc[0])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_manual_input_lowercase_keys()
