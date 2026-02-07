from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class MedallionIsaStrategy(BaseStrategy):
    """
    Medallion ISA Strategy ("Simons-Lite"):
    Designed for UK Retail ISA accounts (Long Only, No Leverage).
    Captures mean reversion opportunities within strong uptrends.

    Logic:
    1. Trend: Price > 200 SMA (Long-term Bullish)
    2. Setup: Price > 50 SMA (Intermediate Bullish)
    3. Trigger: RSI(3) < 15 (Deep short-term oversold condition)
    4. Volume: Volume > 1.5 * 20-day Avg Volume (Institutional Footprint)
    """

    def __init__(self, ticker: str, df: pd.DataFrame, check_mode: bool = False):
        self.ticker = ticker
        self.df = df
        self.check_mode = check_mode

    def analyze(self) -> dict:
        try:
            # Data Hygiene
            df = self.df.copy()
            df = df.dropna(how='all')
            # Need enough data for 200 SMA
            if len(df) < 200: return None

            curr_close = float(df['Close'].iloc[-1])
            curr_volume = float(df['Volume'].iloc[-1])

            # Calculate Indicators
            sma_200 = df['Close'].rolling(200).mean().iloc[-1]
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]

            # Short-term RSI (3-period for fast mean reversion)
            rsi_3 = ta.rsi(df['Close'], length=3)
            current_rsi = rsi_3.iloc[-1] if rsi_3 is not None else 50.0

            # Volume Analysis
            vol_sma_20 = df['Volume'].rolling(20).mean().iloc[-1]
            vol_spike = curr_volume > (vol_sma_20 * 1.5)

            # Logic
            signal = "WAIT"
            verdict_color = "gray"
            score = 0
            action = "WAIT"

            is_uptrend = curr_close > sma_200
            is_setup = curr_close > sma_50
            is_oversold = current_rsi < 15

            if is_uptrend and is_setup and is_oversold:
                if vol_spike:
                    signal = "💎 MEDALLION BUY"
                    verdict_color = "green"
                    score = 95
                    action = "BUY (Aggressive)"
                else:
                    signal = "✅ MEDALLION BUY"
                    verdict_color = "green"
                    score = 85
                    action = "BUY"
            elif is_uptrend and is_setup and current_rsi < 30:
                signal = "👀 WATCH (Oversold)"
                verdict_color = "yellow"
                score = 60
                action = "WATCH"
            elif not is_uptrend:
                signal = "❌ AVOID (Downtrend)"
                verdict_color = "red"
                score = 0
                action = "AVOID"

            # Stop Loss: Low of the setup candle (or slightly below)
            # For robustness, let's use 2 ATR below close
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).iloc[-1]
            stop_loss = curr_close - (2 * atr)

            # Target: Reversion to mean (SMA 20) or RSI > 70
            # Let's use SMA 20 as a dynamic target
            sma_20 = df['Close'].rolling(20).mean().iloc[-1]
            target = max(sma_20, curr_close + (3 * atr)) # Ensure target is above entry

            if signal == "WAIT" or action == "AVOID" or action == "WATCH":
                if not self.check_mode:
                     return None
                # In check mode, we might want to return even if WAIT, but typically screeners return only hits.
                # If we want to support 'check' functionality (single stock check), we return everything.
                if action == "WAIT" and not self.check_mode:
                    return None

            return {
                "ticker": self.ticker,
                "price": curr_close,
                "signal": signal,
                "verdict": signal, # Alias for unified UI
                "action": action,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "score": score,
                "verdict_color": verdict_color,
                "rsi": round(current_rsi, 1),
                "vol_spike": vol_spike,
                "atr_value": round(atr, 2),
                "breakout_level": round(sma_50, 2), # Using SMA 50 as 'support' level for display
                "breakout_date": "Now" if "BUY" in signal else "-"
            }

        except Exception as e:
            logger.error(f"Medallion ISA Strategy Error for {self.ticker}: {e}")
            return None
