from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Abstract Base Class for Screener Strategies.
    All strategies must implement the analyze method.
    """

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyzes a single ticker DataFrame and returns a signal dictionary.

        Args:
            df (pd.DataFrame): The dataframe for the ticker.
                               Should contain Open, High, Low, Close, Volume.

        Returns:
            dict: {
                "signal": str,   # e.g., "BUY", "SELL", "WAIT"
                "verdict": str,  # Detailed verdict e.g. "🚀 BREAKOUT"
                "color": str,    # e.g., "green", "red", "gray"
                "score": float,  # 0-100 confidence
                ... strategy specific fields ...
            }
        """
        raise NotImplementedError
