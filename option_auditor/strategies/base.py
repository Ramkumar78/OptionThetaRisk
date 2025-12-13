from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyzes the given DataFrame and returns a dictionary with:
        - signal: str ("BUY", "SELL", "WAIT", etc.)
        - key metrics...
        """
        pass
