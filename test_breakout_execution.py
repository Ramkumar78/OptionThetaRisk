from option_auditor.screener import _calculate_trend_breakout_date
import pandas as pd
import numpy as np

def test_breakout_exists():
    # Create dummy data
    df = pd.DataFrame({
        'Close': [100]*100,
        'High': [105]*100,
        'Low': [95]*100,
        'Open': [100]*100,
        'Volume': [1000]*100
    }, index=pd.date_range('2023-01-01', periods=100))

    # Just verify it runs without error
    try:
        res = _calculate_trend_breakout_date(df)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    test_breakout_exists()
