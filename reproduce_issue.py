import pandas as pd
import yfinance as yf
from option_auditor.unified_screener import get_market_regime

# Force issue by checking if get_market_regime returns the error
status, note = get_market_regime()
print(f"Status: {status}, Note: {note}")

if note == "SMA Calculation Error":
    print("Issue Reproduced!")
else:
    print("Issue NOT Reproduced (Might be intermittent or fixed)")
