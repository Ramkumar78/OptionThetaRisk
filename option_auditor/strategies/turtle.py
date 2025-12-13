from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta

class TurtleStrategy(BaseStrategy):
    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 21:
            return {'signal': 'WAIT'}

        # Calculate Indicators
        df = df.copy()
        df['20_High'] = df['High'].rolling(window=20).max().shift(1)
        df['20_Low'] = df['Low'].rolling(window=20).min().shift(1)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)

        if pd.isna(df['20_High'].iloc[-1]) or pd.isna(df['ATR'].iloc[-1]):
            return {'signal': 'WAIT'}

        curr_close = float(df['Close'].iloc[-1])
        prev_high = float(df['20_High'].iloc[-1])
        prev_low = float(df['20_Low'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])

        signal = "WAIT"
        stop_loss = 0.0
        target = 0.0

        dist_to_breakout_high = (curr_close - prev_high) / prev_high

        # Buy Breakout
        if curr_close > prev_high:
            signal = "BUY"
            stop_loss = curr_close - (2 * atr)
            target = curr_close + (4 * atr)

        # Sell Breakout
        elif curr_close < prev_low:
            signal = "SELL"
            stop_loss = curr_close + (2 * atr)
            target = curr_close - (4 * atr)

        # Watchlist
        elif -0.02 <= dist_to_breakout_high <= 0:
            signal = "WATCH"
            stop_loss = prev_high - (2 * atr)
            target = prev_high + (4 * atr)

        return {
            "signal": signal,
            "breakout_level": prev_high,
            "stop_loss": stop_loss,
            "target": target,
            "atr": atr
        }
