import pandas as pd
import pandas_ta as ta
from option_auditor.strategies.base import BaseStrategy
from option_auditor.master_screener import FortressScreener
from option_auditor.common.signal_type import SignalType

class GrandmasterStrategy(BaseStrategy):
    """
    Grandmaster Strategy: Adapts the MasterScreener (Council Protocol) logic
    for historical backtesting.
    """

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.name = "Grandmaster"
        # We instantiate the screener to access its internal logic methods if needed
        # Note: The class in master_screener.py is FortressScreener, not MasterScreener
        self.screener = FortressScreener()

    def generate_signals(self, ticker_data: pd.DataFrame) -> pd.DataFrame:
        """
        Applies the Master Screener logic to historical data.
        """
        df = ticker_data.copy()

        # Ensure column names are standardized to lowercase for internal processing
        if 'Close' in df.columns and 'close' not in df.columns:
            df['close'] = df['Close']

        # ------------------------------------------------------------------
        # ADAPTER: Replicating FortressScreener Logic for DataFrame (Vectorized)
        # ------------------------------------------------------------------

        # 1. Setup Indicators (Matching FortressScreener)
        # SMAs: 50, 150, 200
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_150'] = df['close'].rolling(window=150).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()

        # 52 Week High/Low (252 trading days)
        df['High_52'] = df['close'].rolling(window=252).max()
        df['Low_52'] = df['close'].rolling(window=252).min()

        # RSI Calculation (14 period) - Using pandas_ta if possible to match master_screener exactly,
        # but fallback to manual calculation if needed. master_screener uses pandas_ta.
        try:
            # Replicating master_screener logic: ta.rsi(close, length=14)
            df['RSI'] = ta.rsi(df['close'], length=14)
        except Exception:
            # Manual fallback
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rs = rs.fillna(0)
            df['RSI'] = 100 - (100 / (1 + rs))

        # 2. Apply the Logic
        df['signal'] = SignalType.HOLD.value

        # --- LOGIC INSERTION POINT ---
        # Replicating "Trend Template (Minervini)" from FortressScreener

        # Trend Template Conditions:
        # 1. Price > SMA 150 and Price > SMA 200
        cond1 = (df['close'] > df['SMA_150']) & (df['close'] > df['SMA_200'])

        # 2. SMA 150 > SMA 200
        cond2 = (df['SMA_150'] > df['SMA_200'])

        # 3. SMA 50 > SMA 150
        cond3 = (df['SMA_50'] > df['SMA_150'])

        # 4. Price > SMA 50
        cond4 = (df['close'] > df['SMA_50'])

        # 5. Price > 52w Low * 1.3 (30% above low)
        cond5 = (df['close'] > (df['Low_52'] * 1.3))

        # 6. Price > 52w High * 0.75 (Within 25% of high)
        cond6 = (df['close'] > (df['High_52'] * 0.75))

        # Combined Trend Template (Growth Entry)
        trend_template = cond1 & cond2 & cond3 & cond4 & cond5 & cond6

        # Options Income Logic (Dip in Uptrend) from FortressScreener
        # logic: curr_price > sma_200 and rsi < 45 and rsi > 30
        options_income = (
            (df['close'] > df['SMA_200']) &
            (df['RSI'] < 45) &
            (df['RSI'] > 30)
        )

        # Combine signals: Prioritize Growth Trend for BUY signal in backtest
        # Or include Options Income as BUY as well?
        # Master Screener treats both as actionable.
        # Let's map Trend Template to BUY.
        buy_condition = trend_template

        # Apply Buy Signal
        df.loc[buy_condition, 'signal'] = SignalType.BUY.value

        # Note: FortressScreener doesn't have an explicit exit signal logic for backtesting,
        # usually relying on Stop Loss (Low of 20 days) or losing the trend.
        # User snippet suggested: sell if Close < SMA 50.
        sell_condition = (df['close'] < df['SMA_50'])
        df.loc[sell_condition, 'signal'] = SignalType.SELL.value

        return df

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        Implements BaseStrategy abstract method.
        Analyzes the latest state of the DataFrame.
        """
        if df is None or df.empty:
            return {'signal': 'WAIT'}

        # Run vectorised logic
        sig_df = self.generate_signals(df)
        last_signal = sig_df['signal'].iloc[-1]

        return {
            "signal": last_signal,
            "rsi": sig_df['RSI'].iloc[-1] if 'RSI' in sig_df.columns else 0
        }
