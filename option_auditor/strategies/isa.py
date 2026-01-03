import pandas as pd
import pandas_ta as ta
import numpy as np

class IsaStrategy:
    """
    ISA Trend Strategy:
    - Long Term Trend: Price > 200 SMA
    - Momentum: Price within 15% of 52-week High
    - Breakout: Price crosses 50-day High (Donchian Channel)
    - Volatility: ATR logic for stops
    """
    def __init__(self, ticker, df):
        self.ticker = ticker
        self.df = df

    def analyze(self):
        try:
            # Check data sufficiency
            if self.df.empty or len(self.df) < 200:
                return None

            close = self.df['Close']
            high = self.df['High']
            low = self.df['Low']

            curr_price = float(close.iloc[-1])

            # --- INDICATORS ---
            sma_50 = close.rolling(50).mean().iloc[-1]
            sma_150 = close.rolling(150).mean().iloc[-1]
            sma_200 = close.rolling(200).mean().iloc[-1]
            atr = ta.atr(high, low, close, length=14).iloc[-1]

            # 52 Week High Logic
            high_52w = high.rolling(252).max().iloc[-1]
            dist_to_52w = (high_52w - curr_price) / curr_price

            # 50 Day Breakout Logic (Entry Signal)
            high_50d = high.rolling(50).max().shift(1).iloc[-1]
            is_breakout = curr_price > high_50d

            # Trailing Exit (20 Day Low)
            low_20d = low.rolling(20).min().shift(1).iloc[-1]

            # --- RULES ---
            # 1. Trend Alignment (Minervini Template Lite)
            trend_ok = (curr_price > sma_200) and (sma_50 > sma_200)

            # 2. Near Highs (Must be within 25% of 52w highs to be a leader)
            near_highs = dist_to_52w < 0.25

            signal = "WAIT"
            if trend_ok and near_highs and is_breakout:
                signal = "BUY BREAKOUT"
            elif trend_ok and near_highs:
                signal = "WATCHLIST"

            # Stop Loss (3 ATR)
            stop_loss = curr_price - (3 * atr)

            # Formatting for Frontend
            return {
                "Ticker": self.ticker,
                "Price": round(curr_price, 2),
                "Signal": signal,
                "breakout_level": round(high_50d, 2),
                "stop_loss_3atr": round(stop_loss, 2),
                "trailing_exit_20d": round(low_20d, 2),
                "volatility_pct": round((atr / curr_price) * 100, 2),
                "risk_per_share": round(curr_price - stop_loss, 2),
                "tharp_verdict": "BULL" if trend_ok else "BEAR",
                "max_position_size": "20%" # Hardcoded safe limit
            }

        except Exception as e:
            # print(f"ISA Error {self.ticker}: {e}")
            return None
