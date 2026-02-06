from .base import BaseStrategy
import pandas_ta as ta
import pandas as pd
from typing import Tuple

class RsiReversalStrategy(BaseStrategy):
    def __init__(self, strategy_type: str = "rsi_reversal"):
        self.strategy_type = strategy_type

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyze function for Screener/Analyzer.
        """
        if df is None or df.empty:
            return None

        # Ensure indicators
        df = self.add_indicators(df.copy())

        # Check latest signal
        if len(df) < 20: # Need at least 20 for BB
            return None

        i = len(df) - 1
        buy = self.should_buy(i, df, {})
        sell, reason = self.should_sell(i, df, {})

        signal = "WAIT"
        conviction = "Normal"

        if buy:
            signal = "BUY"
            # Retail Sentiment Proxy: High Volume on Oversold
            current_vol = df['Volume'].iloc[i]
            vol_avg = df['vol_sma_20'].iloc[i] if 'vol_sma_20' in df.columns else None

            if vol_avg and current_vol > (1.5 * vol_avg):
                conviction = "High Conviction"

        elif sell:
            signal = "SELL"

        return {
            "signal": signal,
            "rsi": df['rsi'].iloc[-1] if 'rsi' in df.columns else 0,
            "conviction": conviction,
            "price": df['Close'].iloc[-1]
        }

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['rsi'] = ta.rsi(df['Close'], length=14)

        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)

        # Volume SMA
        if 'Volume' in df.columns:
            df['vol_sma_20'] = ta.sma(df['Volume'], length=20)

        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        if i < 1: return False

        # Signal 'BUY' if Price < Lower BB AND RSI < 30
        try:
            current_close = df['Close'].iloc[i]
            current_rsi = df['rsi'].iloc[i]
            # pandas_ta default column name for Lower Band with length 20, std 2
            lower_bb = df['BBL_20_2.0'].iloc[i]
        except KeyError:
            # Fallback or missing indicators
            return False

        if pd.isna(current_close) or pd.isna(current_rsi) or pd.isna(lower_bb):
            return False

        return current_close < lower_bb and current_rsi < 30

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> Tuple[bool, str]:
        if i < 1: return False, ""

        # Signal 'SELL' if RSI crosses below 70 from above (Legacy Logic preserved)
        # Or maybe if Price > Upper BB?
        # Keeping existing logic for now unless requested otherwise,
        # but user only specified BUY conditions.

        current_rsi = df['rsi'].iloc[i]
        prev_rsi = df['rsi'].iloc[i-1]

        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            return False, ""

        if prev_rsi >= 70 and current_rsi < 70:
            return True, "RSI Cross Below 70"

        return False, ""

    def get_initial_stop_target(self, row: pd.Series, atr: float) -> Tuple[float, float]:
        # Stop-loss: 2% below entry price.
        price = row['Close']
        stop_loss = price * 0.98
        target_price = 0.0 # No fixed target, rely on sell signal

        return stop_loss, target_price
