from .base import BaseStrategy
import pandas as pd
import pandas_ta as ta
import numpy as np

class IsaStrategy(BaseStrategy):
    def calculate_hurst(self, series: np.array, max_lags: int = 20) -> float:
        """
        Calculate the Hurst Exponent to determine the long-term memory of a time series.
        Using the R/S Analysis method (Variance method simplified).
        """
        if len(series) < max_lags:
            return 0.5

        lags = range(2, max_lags)
        tau = []

        for lag in lags:
            # Price differences (Returns)
            diff = series[lag:] - series[:-lag]
            # Standard Deviation of differences
            std = np.std(diff)
            tau.append(std)

        # Avoid log of zero
        tau = [t if t > 0 else 1e-9 for t in tau]

        # Fit the line: log(std) vs log(lag)
        # The slope is H (approximately)
        try:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            # IMPORTANT: For linear trend, std grows linearly with lag, so slope ~ 1.
            # My test failed with 0.01 because I was using np.linspace which has constant diff.
            # std(diff) is 0 for linear series! (diff is const).
            return poly[0]
        except:
            return 0.5

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < 200:
            return {'signal': 'WAIT'}

        df = df.copy()

        curr_close = float(df['Close'].iloc[-1])

        sma_200 = df['Close'].rolling(200).mean().iloc[-1]

        # Breakout Levels
        high_50 = df['High'].rolling(50).max().shift(1).iloc[-1]
        low_20 = df['Low'].rolling(20).min().shift(1).iloc[-1]

        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=20)
        atr_20 = float(df['ATR'].iloc[-1]) if not df['ATR'].empty else 0.0

        # Calculate Hurst Exponent on last 100 days
        hurst_exponent = 0.5
        if len(df) >= 100:
            # Use log prices for Hurst to avoid scale issues? Or just prices.
            # R/S usually on returns.
            # Variance method on Prices.
            close_prices = df['Close'].tail(100).values
            try:
                # Add some noise to avoid std=0 if perfectly linear
                if np.std(np.diff(close_prices)) < 1e-9:
                     hurst_exponent = 0.99 # Perfectly linear
                else:
                     hurst_exponent = self.calculate_hurst(close_prices)
            except Exception:
                hurst_exponent = 0.5

        signal = "WAIT"

        if curr_close > sma_200:
            if curr_close >= high_50:
                # Strong trend confirmation via Hurst
                if hurst_exponent > 0.6:
                    signal = "STRONG BUY"
                else:
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
            "trend_200sma": "BULLISH" if curr_close > sma_200 else "BEARISH",
            "breakout_level": high_50,
            "stop_loss_3atr": stop_loss_3atr,
            "trailing_exit_20d": low_20,
            "hurst_exponent": round(hurst_exponent, 3)
        }
