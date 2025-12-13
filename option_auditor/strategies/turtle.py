from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta

class TurtleStrategy(BaseStrategy):
    """
    Turtle Trading Strategy (20-Day Breakout).
    """
    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < 21:
            return {"signal": "WAIT", "verdict": "Insufficient Data", "color": "gray", "score": 0}

        # 1. Donchian Channels (20-day High/Low)
        # Shift(1) to compare Close vs Previous High
        high_20 = df['High'].rolling(window=20).max().shift(1).iloc[-1]
        low_20 = df['Low'].rolling(window=20).min().shift(1).iloc[-1]

        # 2. ATR
        atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=20)
        atr = float(atr_series.iloc[-1]) if atr_series is not None else 0.0

        curr_close = float(df['Close'].iloc[-1])

        if pd.isna(high_20):
            return {"signal": "WAIT", "verdict": "N/A", "color": "gray", "score": 0}

        signal = "WAIT"
        verdict = "WAIT"
        color = "gray"
        score = 0

        # Stop / Target placeholders
        stop_loss = 0.0
        target = 0.0

        # Logic
        if curr_close > high_20:
            signal = "BUY"
            verdict = "🚀 BREAKOUT (BUY)"
            color = "green"
            score = 100
            stop_loss = curr_close - (2 * atr)
            target = curr_close + (4 * atr)

        elif curr_close < low_20:
            signal = "SELL"
            verdict = "📉 BREAKDOWN (SELL)"
            color = "red"
            score = 100 # High confidence sell
            stop_loss = curr_close + (2 * atr)
            target = curr_close - (4 * atr)

        elif (high_20 - curr_close) / high_20 < 0.02:
            signal = "WATCH"
            verdict = "👀 WATCH (Near High)"
            color = "yellow"
            score = 50

        return {
            "signal": signal,
            "verdict": verdict,
            "color": color,
            "score": score,
            "breakout_level": high_20,
            "breakdown_level": low_20,
            "stop_loss": stop_loss,
            "target": target,
            "atr": atr
        }
