from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
from option_auditor.quant_engine import QuantPhysicsEngine

class IsaStrategy(BaseStrategy):
    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 200:
            return {'signal': 'WAIT'}

        df = df.copy()

        curr_close = float(df['Close'].iloc[-1])

        # UPGRADE: Replace SMA with Kalman DSP
        # We need numpy array for Kalman
        try:
            kalman_trend = QuantPhysicsEngine.kalman_filter(df['Close'])
            df['Kalman_Trend'] = kalman_trend
            current_kalman = float(kalman_trend.iloc[-1])
        except Exception:
            # Fallback if Kalman fails (e.g. library issue)
            current_kalman = df['Close'].rolling(200).mean().iloc[-1]

        # Breakout Levels
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        low_20 = df['Low'].rolling(20).min().shift(1).iloc[-1]

        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)
        atr_20 = float(df['ATR'].iloc[-1]) if not df['ATR'].empty else 0.0

        signal = "WAIT"

        # New physical condition for entry: Price > Kalman Trend
        if curr_close > current_kalman:
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
            "trend_200sma": "BULLISH" if curr_close > current_kalman else "BEARISH", # Label kept as 200sma for compatibility
            "breakout_level": high_50,
            "stop_loss_3atr": stop_loss_3atr,
            "trailing_exit_20d": low_20,
            "kalman_trend": current_kalman
        }
