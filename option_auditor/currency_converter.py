from __future__ import annotations
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict

class CurrencyConverter:
    """
    Converts currency amounts using historical FX rates from yfinance.
    """
    def __init__(self, base_currency: str = 'USD'):
        self.base_currency = base_currency
        self.rate_cache: Dict[str, pd.DataFrame] = {}

    def get_rate(self, from_currency: str, to_currency: str, date: datetime | pd.Timestamp) -> float:
        """
        Fetches the FX rate for from_currency -> to_currency on the given date.
        """
        if from_currency == to_currency:
            return 1.0

        pair = f"{from_currency}{to_currency}=X"

        # Check cache
        if pair not in self.rate_cache:
            try:
                # Fetch last 10 years to cover most history
                ticker = yf.Ticker(pair)
                # period="10y" covers reasonable backtest history
                hist = ticker.history(period="10y")
                if hist.empty:
                    print(f"Warning: No history found for {pair}")
                    return 1.0
                self.rate_cache[pair] = hist
            except Exception as e:
                print(f"Error fetching rate for {pair}: {e}")
                return 1.0

        hist = self.rate_cache[pair]

        # Look up date
        ts = pd.Timestamp(date).normalize()

        # Ensure timezone compatibility
        if ts.tzinfo is None and hist.index.tz is not None:
             ts = ts.tz_localize(hist.index.tz)
        elif ts.tzinfo is not None and hist.index.tz is None:
             ts = ts.tz_convert(None)

        try:
             # Use get_indexer with method='pad' (ffill) to find nearest previous date
             idx_loc = hist.index.get_indexer([ts], method='pad')[0]

             if idx_loc == -1:
                 # Date is before start of history
                 # Fallback to the first available rate
                 return hist['Close'].iloc[0]

             return hist['Close'].iloc[idx_loc]
        except Exception as e:
            print(f"Error extracting rate for {pair} at {date}: {e}")
            return 1.0

    def convert(self, amount: float, from_currency: str, date: datetime | pd.Timestamp, to_currency: Optional[str] = None) -> float:
        """
        Converts amount from_currency to to_currency (defaults to base_currency).
        """
        target_currency = to_currency if to_currency else self.base_currency
        rate = self.get_rate(from_currency, target_currency, date)
        return amount * rate
