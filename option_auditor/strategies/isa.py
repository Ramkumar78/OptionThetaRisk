from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta

class IsaStrategy(BaseStrategy):
    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 200:
            return {'signal': 'WAIT'}

        df = df.copy()

        curr_close = float(df['Close'].iloc[-1])

        # Liquidity Check (Assuming passed df is for one ticker and might need volume check)
        # Unified screener might handle this or we do it here.
        # But for 'analyze', we just process data.

        sma_200 = df['Close'].rolling(200).mean().iloc[-1]

        # Breakout Levels
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        low_20 = df['Low'].rolling(20).min().shift(1).iloc[-1]

        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)
        atr_20 = float(df['ATR'].iloc[-1]) if not df['ATR'].empty else 0.0

        signal = "WAIT"

        if curr_close > sma_200:
            if curr_close >= high_50:
                signal = "BUY"
            elif curr_close >= high_50 * 0.98:
                signal = "WATCH"
            elif curr_close > low_20:
                signal = "HOLD"
            elif curr_close <= low_20:
                signal = "EXIT"
        else:
            signal = "AVOID" # Downtrend

        stop_loss_3atr = curr_close - (3 * atr_20)

        return {
            "signal": signal,
            "trend_200sma": "BULLISH" if curr_close > sma_200 else "BEARISH",
            "breakout_level": high_50,
            "stop_loss_3atr": stop_loss_3atr,
            "trailing_exit_20d": low_20
        }
