from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import logging
import yfinance as yf
from option_auditor.common.constants import TICKER_NAMES

logger = logging.getLogger(__name__)

class Quality200wStrategy(BaseStrategy):
    """
    Quality 200-Week MA Strategy:
    - Universe: Any ticker (US/UK).
    - Signal: Price <= 200-Week SMA (+1% tolerance).
    - Quality Filter: Price > 50-Day SMA.
    - Fundamental: Positive 3-Year Revenue Growth.
    """
    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode

    def analyze(self) -> dict:
        if self.df is None or self.df.empty:
            return None

        df = self.df.copy()

        # 1. Calculate 50-Day SMA (Daily)
        # Ensure we have enough data
        if len(df) < 50:
            return None

        # pandas_ta might return None if insufficient data
        sma_50_series = ta.sma(df['Close'], length=50)
        if sma_50_series is None or sma_50_series.empty:
            return None

        df['SMA_50'] = sma_50_series

        current_price = df['Close'].iloc[-1]
        current_sma_50 = df['SMA_50'].iloc[-1]

        if pd.isna(current_sma_50):
            return None

        # Condition 2: Quality Filter (Price > 50-Day SMA)
        if current_price <= current_sma_50:
            return None

        # 2. Resample to Weekly for 200-Week SMA
        # 'W' frequency corresponds to weekly
        df_weekly = df.resample('W').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })

        # We need at least 200 weeks
        if len(df_weekly) < 200:
            return None

        sma_200_weekly_series = ta.sma(df_weekly['Close'], length=200)
        if sma_200_weekly_series is None or sma_200_weekly_series.empty:
            return None

        df_weekly['SMA_200'] = sma_200_weekly_series

        current_sma_200 = df_weekly['SMA_200'].iloc[-1]

        if pd.isna(current_sma_200):
            return None

        # Condition 1: Signal Condition
        # BUY if Price <= 200-week SMA * 1.01
        upper_limit = current_sma_200 * 1.01

        if current_price > upper_limit:
            return None

        # Condition 3: Positive 3-Year Revenue Growth
        # Using yfinance info as proxy if financials fetch is too heavy/complex
        # or actually fetch financials if feasible.
        # Given "if fundamental data is available", we proceed if we can confirm positive.
        # If unavailable, we might skip or include. Strategy usually implies "Quality" means verified quality.
        # I'll check 'revenueGrowth' from info (YoY) and try to check financials if possible.

        is_quality = False
        try:
            ticker_obj = yf.Ticker(self.ticker)
            info = ticker_obj.info

            # Check 1: Info 'revenueGrowth'
            if info.get('revenueGrowth', 0) > 0:
                is_quality = True

            # Check 2: Financials (3-year) if not confirmed or to be more strict?
            # User asked "positive 3-year revenue growth".
            # YoY growth (revenueGrowth) is 1 year.
            # I should try to get financials.

            financials = ticker_obj.financials
            if not financials.empty and 'Total Revenue' in financials.index:
                revs = financials.loc['Total Revenue']
                # revs is typically latest to oldest
                if len(revs) >= 4:
                    # Compare Year 0 (Latest) vs Year 3 (3 years ago)
                    # If Year 0 > Year 3, growth is positive over 3 years.
                    growth_3y = revs.iloc[0] > revs.iloc[3]
                    if growth_3y:
                        is_quality = True
                    else:
                        is_quality = False # Explicitly fail if data shows negative 3y growth
                elif len(revs) >= 2:
                    # Fallback to whatever history we have
                    if revs.iloc[0] > revs.iloc[-1]:
                        is_quality = True
                    else:
                        is_quality = False

            # If financials empty, stick to info 'revenueGrowth' result

        except Exception as e:
            logger.debug(f"Fundamental check failed for {self.ticker}: {e}")
            # If failed to check, assume True? Or False?
            # "Only include stocks where ... (if fundamental data is available)"
            # If not available, maybe exclude? Or include?
            # Let's assume if we can't verify, we include if we have price signal,
            # OR exclude to ensure "Quality".
            # The name "Quality" implies we want to filter out trash.
            # But missing data != trash.
            # I'll default to True if data is completely missing to avoid empty results for obscure tickers,
            # but if data is present and negative, is_quality will be set to False.
            is_quality = True

        if not is_quality:
            return None

        # Prepare Result
        pct_distance = ((current_price - current_sma_200) / current_sma_200) * 100
        verdict = "BUY (Quality Dip)"
        company_name = TICKER_NAMES.get(self.ticker, self.ticker)

        return {
            "ticker": self.ticker,
            "company_name": company_name,
            "price": current_price,
            "sma_200_week": round(current_sma_200, 2),
            "distance_pct": round(pct_distance, 2),
            "verdict": verdict,
            "signal": verdict,
            "sma_50_day": round(current_sma_50, 2)
        }

    def get_retail_explanation(self) -> str:
        return "Buying quality stocks (positive revenue growth) in an uptrend (above 50-day SMA) pulling back to long-term support (200-week SMA)."
