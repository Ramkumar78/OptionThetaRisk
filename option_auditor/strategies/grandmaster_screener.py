import pandas as pd
import pandas_ta as ta
import numpy as np
from option_auditor.strategies.base import BaseStrategy
from option_auditor.common.signal_type import SignalType

class GrandmasterScreener(BaseStrategy):
    """
    Grandmaster Screener (The 'Hardened' ISA Logic):
    A professional trend-following strategy that focuses on capital preservation
    and catching high-momentum outliers.

    Key Upgrades from Original:
    1. Entry: Event-based (20-Day Breakout + Volume Spike) rather than State-based.
    2. Exit: Volatility-adjusted (ATR) and Trailing 20-Day Lows.
    3. Filter: Relative Volume (RVol) check to prevent fakeouts.
    """

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.name = "GrandmasterScreener"

    def generate_signals(self, ticker_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy/sell signals on historical data using vectorised logic.
        """
        df = ticker_data.copy()

        # Standardise columns
        if 'Close' in df.columns and 'close' not in df.columns:
            df['close'] = df['Close']
        if 'High' in df.columns and 'high' not in df.columns:
            df['high'] = df['High']
        if 'Low' in df.columns and 'low' not in df.columns:
            df['low'] = df['Low']
        if 'Volume' in df.columns and 'volume' not in df.columns:
            df['volume'] = df['Volume']

        # ------------------------------------------------------------------
        # 1. INDICATORS
        # ------------------------------------------------------------------
        # Trend Moving Averages
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_150'] = df['close'].rolling(window=150).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()

        # Volatility (ATR 14)
        # using pandas_ta if available, else manual
        try:
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        except AttributeError:
             # Fallback manual ATR
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['close'].shift(1))
            tr3 = abs(df['low'] - df['close'].shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()

        # 52 Week High/Low (252 days)
        df['High_52'] = df['close'].rolling(window=252).max()
        df['Low_52'] = df['close'].rolling(window=252).min()

        # Donchian Channels (20 Day) for Breakouts & Trailing Exits
        # Shift(1) is critical: We want to break the *previous* 20 day high
        df['Donchian_High_20'] = df['high'].rolling(window=20).max().shift(1)
        df['Donchian_Low_20'] = df['low'].rolling(window=20).min().shift(1)

        # Volume Analytics
        df['Vol_SMA_20'] = df['volume'].rolling(window=20).mean()
        df['RVol'] = df['volume'] / df['Vol_SMA_20']

        # ------------------------------------------------------------------
        # 2. LOGIC (The "Hardened" Rules)
        # ------------------------------------------------------------------
        df['signal'] = SignalType.HOLD.value

        # --- A. TREND TEMPLATE (Minervini) ---
        # The 'State' required before looking for an entry
        trend_ok = (
            (df['close'] > df['SMA_200']) &
            (df['SMA_50'] > df['SMA_200']) &
            (df['close'] > df['SMA_50']) &
            (df['close'] > (df['Low_52'] * 1.25)) &  # 25% off lows
            (df['close'] > (df['High_52'] * 0.75))   # Within 25% of highs (Leader)
        )

        # --- B. THE TRIGGER (Entry) ---
        # 1. Price breaks 20-Day High (Donchian Breakout)
        # 2. Volume is > 120% of average (Institutional Footprint)
        breakout_trigger = (
            (df['close'] > df['Donchian_High_20']) &
            (df['RVol'] > 1.2)
        )

        buy_condition = trend_ok & breakout_trigger

        # --- C. THE EXIT (Risk Management) ---
        # In a vectorised backtest without state, we use the Trailing 20-Day Low
        # as a proxy for the "Trailing Stop".
        # (Note: The ATR stop is calculated in 'analyze' for live trading,
        # but 20d Low is a robust proxy for historical trends).
        sell_condition = (df['close'] < df['Donchian_Low_20'])

        # Apply Signals
        df.loc[buy_condition, 'signal'] = SignalType.BUY.value
        df.loc[sell_condition, 'signal'] = SignalType.SELL.value

        return df

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Analyzes the latest state for the Live Screener Dashboard.
        Calculates exact Stop Loss levels based on ATR.
        """
        if df is None or df.empty or len(df) < 200:
            return {'signal': 'WAIT'}

        # Run vectorised logic to get the latest signal status
        sig_df = self.generate_signals(df)

        last_row = sig_df.iloc[-1]
        curr_price = last_row['close']
        atr = last_row['ATR']
        signal = last_row['signal']

        # Logic for "Watchlist" vs "Buy"
        # If trend is OK but no breakout yet, we watch it.
        trend_ok = (
            (curr_price > last_row['SMA_200']) and
            (last_row['SMA_50'] > last_row['SMA_200']) and
            (curr_price > last_row['High_52'] * 0.75)
        )

        if signal == SignalType.BUY.value:
            final_signal = "BUY BREAKOUT"
        elif trend_ok:
            final_signal = "WATCHLIST"
        elif signal == SignalType.SELL.value:
            final_signal = "SELL/AVOID"
        else:
            final_signal = "WAIT"

        # Hardened Stop Loss Calculation (The "Life Depends on It" Number)
        # 2.5 x ATR is a standard "Swing" width that avoids noise but kills losers.
        stop_loss_price = curr_price - (2.5 * atr)

        # Position Sizing Logic (Risk Based)
        # Assuming 1% Account Risk.
        # e.g. If Account £10k, Risk £100.
        # Risk Per Share = £100 - £90 = £10.
        # Shares = 100 / 10 = 10.
        risk_per_share = curr_price - stop_loss_price

        return {
            "signal": final_signal,
            "price": round(curr_price, 2),
            "stop_loss_atr": round(stop_loss_price, 2),
            "trailing_exit_20d": round(last_row['Donchian_Low_20'], 2),
            "volatility_atr": round(atr, 2),
            "rvol": round(last_row['RVol'], 2),
            "risk_per_share": round(risk_per_share, 2),
            "breakout_level": round(last_row['Donchian_High_20'], 2),
            "quality_score": round((last_row['RVol'] * 10) + (100 if trend_ok else 0), 2)
        }
