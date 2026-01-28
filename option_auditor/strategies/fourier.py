from .base import BaseStrategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.strategies.math_utils import calculate_hilbert_phase, calculate_dominant_cycle

class FourierStrategy(BaseStrategy):
    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode

    def analyze(self) -> dict:
        try:
            df = self.df
            ticker = self.ticker

            df = df.dropna(how='all')
            if len(df) < 50: return None

            # --- DSP PHYSICS CALCULATION ---
            # Use 'Close' series values
            closes = df['Close'].values

            phase, strength = calculate_hilbert_phase(closes)

            if phase is None: return None

            # --- SIGNAL LOGIC (Based on Radians) ---
            # Phase -3.14 (or 3.14) is the TROUGH (Bottom)
            # Phase 0 is the ZERO CROSSING (Midpoint/Trend)
            # Phase 1.57 (pi/2) is the PEAK (Top)

            # Normalize phase for display (-1 to 1 scale roughly)
            norm_phase = phase / np.pi

            signal = "WAIT"
            verdict_color = "gray"

            # Sine Wave Cycle logic:
            # We want to catch the turn UP from the bottom.
            # Bottom is +/- pi. As it crosses from negative to positive?
            # Actually, Hilbert Phase moves continuously.
            # Deep cycle low is typically near +/- pi boundaries depending on convention.

            # Simplify: If Phase is turning from Negative to Positive (Sine wave bottom)

            if 0.8 <= abs(norm_phase) <= 1.0:
                signal = "🌊 CYCLICAL LOW (Bottoming)"
                verdict_color = "green"
            elif 0.0 <= abs(norm_phase) <= 0.2:
                signal = "🏔️ CYCLICAL HIGH (Topping)"
                verdict_color = "red"

            # Filter weak cycles (Noise)
            if strength < 0.02: # 2% Amplitude threshold
                signal = "WAIT (Weak Cycle)"
                verdict_color = "gray"

            pct_change_1d = None
            if len(df) >= 2:
                pct_change_1d = ((closes[-1] - closes[-2]) / closes[-2]) * 100

            # Calculate dominant period for context
            period, rel_pos = calculate_dominant_cycle(closes) or (0, 0)

            # ATR for Stop/Target
            if 'ATR' not in df.columns:
                 df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

            current_atr = 0.0
            if 'ATR' in df.columns and not df['ATR'].empty:
                 current_atr = df['ATR'].iloc[-1]

            # Mean Reversion Logic: Stop 2 ATR, Target 2 ATR
            curr_price = float(closes[-1])
            if "LOW" in signal:
                stop_loss = curr_price - (2 * current_atr)
                target = curr_price + (2 * current_atr)
            elif "HIGH" in signal:
                stop_loss = curr_price + (2 * current_atr)
                target = curr_price - (2 * current_atr)
            else:
                stop_loss = curr_price - (2 * current_atr)
                target = curr_price + (2 * current_atr)

            breakout_date = _calculate_trend_breakout_date(df)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": float(closes[-1]),
                "pct_change_1d": pct_change_1d,
                "signal": signal,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "cycle_phase": f"{phase:.2f} rad",
                "cycle_strength": f"{strength*100:.1f}%", # Volatility of the cycle
                "verdict_color": verdict_color,
                "method": "Hilbert (Non-Stationary)",
                "cycle_period": f"{period} days", # Legacy compatibility for tests
                "breakout_date": breakout_date,
                "atr_value": round(current_atr, 2),
                "atr": round(current_atr, 2)
            }

        except Exception:
            return None
