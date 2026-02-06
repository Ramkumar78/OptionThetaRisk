import yfinance as yf
import pandas as pd
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from option_auditor.config import BACKTEST_BENCHMARK_SYMBOLS

logger = logging.getLogger("BacktestDataLoader")

class BacktestDataLoader:
    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type(Exception), reraise=True)
    def _download_with_retry(self, symbols, period="10y"):
        return yf.download(symbols, period=period, auto_adjust=True, progress=False)

    def fetch_data(self, ticker: str) -> Optional[pd.DataFrame]:
        try:
            ticker = ticker.upper()
            # Fetch 10 years to ensure 200 SMA is ready before the 5-year backtest starts
            symbols = [ticker] + BACKTEST_BENCHMARK_SYMBOLS
            # Remove duplicates if any
            symbols = list(set(symbols))

            data = self._download_with_retry(symbols, period="10y")

            if isinstance(data.columns, pd.MultiIndex):
                try:
                    close = data['Close']
                    high = data['High']
                    low = data['Low']
                    open_price = data['Open']
                    vol = data['Volume']
                except KeyError:
                     # yfinance structure variations or missing data
                     return None
            else:
                return None

            def get_series(df, sym):
                if sym in df.columns: return df[sym]
                # Fallback
                return pd.Series(dtype=float)

            # Construct dictionary for DataFrame creation
            data_dict = {
                'close': get_series(close, ticker),
                'high': get_series(high, ticker),
                'low': get_series(low, ticker),
                'open': get_series(open_price, ticker),
                'volume': get_series(vol, ticker),
            }

            # Explicit mapping for known benchmarks to match expected column names (Spy, Vix)
            # This maintains compatibility with existing strategies that look for 'Spy' and 'Vix'
            if "SPY" in BACKTEST_BENCHMARK_SYMBOLS:
                data_dict['spy'] = get_series(close, 'SPY')

            if "^VIX" in BACKTEST_BENCHMARK_SYMBOLS:
                data_dict['vix'] = get_series(close, '^VIX')

            df = pd.DataFrame(data_dict).dropna()

            # Capitalize columns: Close, High, Low, Open, Volume, Spy, Vix
            df.columns = [c.capitalize() for c in df.columns]

            return df
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return None
