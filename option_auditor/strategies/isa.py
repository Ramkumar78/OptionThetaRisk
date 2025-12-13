from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta

class IsaStrategy(BaseStrategy):
    """
    ISA Trend Following Strategy (Long Only).
    """
    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < 200:
            return {"signal": "WAIT", "verdict": "Insufficient Data (Need 200d)", "color": "gray", "score": 0}

        curr_close = float(df['Close'].iloc[-1])
        sma_200 = df['Close'].rolling(200).mean().iloc[-1]

        # 50-Day High (Entry) & 20-Day Low (Exit)
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        low_20 = df['Low'].rolling(20).min().shift(1).iloc[-1]

        atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=20)
        atr = float(atr_series.iloc[-1]) if atr_series is not None else 0.0

        signal = "WAIT"
        verdict = "WAIT"
        color = "gray"
        score = 0

        stop_loss = 0.0

        if curr_close > sma_200:
            if curr_close >= high_50:
                signal = "BUY"
                verdict = "🚀 ENTER LONG"
                color = "green"
                score = 100
                stop_loss = curr_close - (3 * atr)

            elif curr_close >= high_50 * 0.98:
                signal = "WATCH"
                verdict = "👀 WATCH (Near Breakout)"
                color = "yellow"
                score = 60

            elif curr_close > low_20:
                signal = "HOLD"
                verdict = "✅ HOLD"
                color = "green"
                score = 50 # Already in
                stop_loss = low_20

            elif curr_close <= low_20:
                signal = "EXIT"
                verdict = "🛑 EXIT (Stop Hit)"
                color = "red"
                score = 0 # Out
        else:
            signal = "AVOID"
            verdict = "❌ AVOID (Downtrend)"
            color = "red"
            score = 0

        return {
            "signal": signal,
            "verdict": verdict,
            "color": color,
            "score": score,
            "sma_200": sma_200,
            "entry_level": high_50,
            "exit_level": low_20,
            "stop_loss": stop_loss
        }
