import pandas as pd
import pandas_ta as ta
import numpy as np
# Fix 1: Import the shared helper function for breakout dates
from option_auditor.common.data_utils import _calculate_trend_breakout_date

class IsaStrategy:
    """
    ISA Trend Strategy:
    - Long Term Trend: Price > 200 SMA
    - Momentum: Price within 15% of 52-week High
    - Breakout: Price crosses 50-day High (Donchian Channel)
    - Volatility: ATR logic for stops
    """
    def __init__(self, ticker, df, account_size=None, risk_per_trade_pct=0.01):
        self.ticker = ticker
        self.df = df
        self.account_size = account_size
        self.risk_per_trade_pct = risk_per_trade_pct

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

            # Fix 2: Filter out "WAIT" signals so the screener only populates Buy/Watch stocks
            if signal == "WAIT":
                return None

            # Fix 3: Calculate the Breakout Date using the helper
            breakout_date = _calculate_trend_breakout_date(self.df)

            # Stop Loss (3 ATR)
            stop_loss = curr_price - (3 * atr)

            # --- POSITION SIZING LOGIC ---
            position_size_shares = 0
            position_value = 0.0
            risk_amount = 0.0
            account_used_pct = 0.0
            max_position_size_str = "20%" # Default fallback

            if self.account_size and self.account_size > 0:
                # Explicit sizing based on risk
                risk_amount = self.account_size * self.risk_per_trade_pct

                # Prevent div by zero
                # If stop is at or above price (which shouldn't happen for long), use min risk
                risk_dist = max(0.01, curr_price - stop_loss)

                # Calculate shares based on risk
                raw_shares = risk_amount / risk_dist

                # Cap at 20% of account (Max Allocation Rule)
                max_allocation = self.account_size * 0.20
                max_shares_allocation = max_allocation / curr_price

                final_shares = int(min(raw_shares, max_shares_allocation))

                position_value = final_shares * curr_price
                account_used_pct = (position_value / self.account_size) * 100

                position_size_shares = final_shares
                max_position_size_str = f"{final_shares} shares (£{int(position_value)})"

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
                "max_position_size": max_position_size_str,
                "shares": position_size_shares,
                "position_value": round(position_value, 2),
                "risk_amount": round(risk_amount, 2),
                "account_used_pct": round(account_used_pct, 1),
                "breakout_date": breakout_date # Fix 4: Populate the field
            }

        except Exception as e:
            # print(f"ISA Error {self.ticker}: {e}")
            return None
