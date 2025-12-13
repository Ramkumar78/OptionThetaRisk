from .base import BaseStrategy
from .utils import calculate_dominant_cycle
import pandas as pd

class FourierStrategy(BaseStrategy):
    """
    Fourier Cycle Analysis Strategy.
    """
    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < 100:
             return {"signal": "WAIT", "verdict": "Insufficient Data", "color": "gray", "score": 0}

        closes = df['Close'].tolist()
        cycle_data = calculate_dominant_cycle(closes)

        if not cycle_data:
             return {"signal": "WAIT", "verdict": "No Cycle Found", "color": "gray", "score": 0}

        period, rel_pos = cycle_data

        signal = "WAIT"
        verdict = "NEUTRAL"
        color = "gray"
        score = 50

        # Logic
        if 5 <= period <= 60:
            if rel_pos <= -0.8:
                signal = "BUY"
                verdict = "🌊 CYCLICAL LOW"
                color = "green"
                score = 90
            elif rel_pos >= 0.8:
                signal = "SELL"
                verdict = "🏔️ CYCLICAL HIGH"
                color = "red"
                score = 90
            elif -0.2 <= rel_pos <= 0.2:
                signal = "WAIT"
                verdict = "➡️ MID-CYCLE"
                color = "gray"
                score = 50
        else:
             verdict = "Cycle Noise/Trend"

        return {
            "signal": signal,
            "verdict": verdict,
            "color": color,
            "score": score,
            "cycle_period": period,
            "cycle_position": rel_pos
        }
