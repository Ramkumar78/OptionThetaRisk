from abc import ABC, abstractmethod
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyzes the given DataFrame and returns a dictionary with:
        - signal: str ("BUY", "SELL", "WAIT", etc.)
        - key metrics...
        """
        pass

    def check_market_volatility(self, df: pd.DataFrame, volatility_multiplier: float = 5.0) -> str | None:
        """
        Financial Breaker: If 1-day ATR is 5x the norm, trip 'AVOID' state.
        This acts as a 'Risk Management Circuit Breaker'.
        """
        if df is None or df.empty or 'ATR' not in df.columns:
            return None

        try:
            current_atr = df['ATR'].iloc[-1]
            mean_atr = df['ATR'].mean()

            # If current ATR is > 5x the average, market is too crazy
            if mean_atr > 0 and current_atr > (mean_atr * volatility_multiplier):
                return "TRIPPED: HIGH VOLATILITY"
        except Exception as e:
            logger.debug(f"Volatility check failed: {e}")

        return None
