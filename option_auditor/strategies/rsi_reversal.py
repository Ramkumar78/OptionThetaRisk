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
        if len(df) < 2:
            return None

        i = len(df) - 1
        buy = self.should_buy(i, df, {})
        sell, reason = self.should_sell(i, df, {})

        signal = "WAIT"
        if buy: signal = "BUY"
        elif sell: signal = "SELL"

        return {
            "signal": signal,
            "rsi": df['rsi'].iloc[-1] if 'rsi' in df.columns else 0
        }

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df['rsi'] = ta.rsi(df['Close'], length=14)
        return df

    def should_buy(self, i: int, df: pd.DataFrame, context: dict) -> bool:
        if i < 1: return False

        # Signal 'BUY' if RSI crosses above 30 from below.
        # i is current, i-1 is previous
        current_rsi = df['rsi'].iloc[i]
        prev_rsi = df['rsi'].iloc[i-1]

        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            return False

        return prev_rsi <= 30 and current_rsi > 30

    def should_sell(self, i: int, df: pd.DataFrame, context: dict) -> Tuple[bool, str]:
        if i < 1: return False, ""

        # Signal 'SELL' if RSI crosses below 70 from above.
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
