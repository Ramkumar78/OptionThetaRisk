import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MasterBacktester")

class MasterBacktester:
    def __init__(self, ticker, initial_capital=10000.0):
        self.ticker = ticker.upper()
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.shares = 0
        self.state = "OUT"
        self.history = []
        self.trade_log = []

    def fetch_data(self):
        """Fetches 2y of data for Ticker, SPY, and VIX to simulate regime."""
        try:
            # Download data
            symbols = [self.ticker, "SPY", "^VIX"]
            # Fetch 3 years to allow for 200 SMA warmup
            data = yf.download(symbols, period="3y", auto_adjust=True, progress=False)

            # Handle MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten or extract
                try:
                    close = data['Close'].copy()
                    high = data['High'].copy()
                    low = data['Low'].copy()
                    vol = data['Volume'].copy()
                except KeyError:
                    # Case where columns might not match expected structure exactly
                    # Sometimes yfinance returns different structures if one ticker fails
                    logger.error("Data structure mismatch in MultiIndex")
                    return None
            else:
                # Fallback if single ticker (unlikely with list)
                return None

            # Check if we have data for all required tickers
            if self.ticker not in close.columns or 'SPY' not in close.columns or '^VIX' not in close.columns:
                 logger.error(f"Missing data for one of the symbols: {symbols}")
                 return None

            # Prepare individual DataFrames
            df = pd.DataFrame({
                'close': close[self.ticker],
                'high': high[self.ticker],
                'low': low[self.ticker],
                'volume': vol[self.ticker],
                'spy': close['SPY'],
                'vix': close['^VIX']
            }).dropna()

            return df
        except Exception as e:
            logger.error(f"Backtest Data Error: {e}")
            return None

    def calculate_indicators(self, df):
        # Market Regime Indicators
        df['spy_sma200'] = df['spy'].rolling(200).mean()

        # Stock Trend Indicators (Minervini)
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma150'] = df['close'].rolling(150).mean()
        df['sma200'] = df['close'].rolling(200).mean()

        # Volatility
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Breakout Signals (20-Day High)
        df['donchian_high'] = df['high'].rolling(20).max().shift(1) # Yesterday's 20-day high
        df['donchian_low'] = df['low'].rolling(20).min().shift(1)   # Yesterday's 20-day low (Trailing Stop)

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None or df.empty:
            return {"error": "No data found"}

        df = self.calculate_indicators(df)

        # Start simulation from 2 years ago (trim the warmup data)
        start_date = pd.Timestamp.now() - pd.DateOffset(years=2)
        sim_data = df[df.index >= start_date].copy()

        if sim_data.empty:
            return {"error": "Not enough data for 2-year simulation"}

        # Buy & Hold Comparison
        initial_price = sim_data['close'].iloc[0]
        final_price = sim_data['close'].iloc[-1]
        bnh_return = ((final_price - initial_price) / initial_price) * 100

        # Strategy Loop
        stop_loss = 0.0

        for date, row in sim_data.iterrows():
            price = row['close']

            # --- RULES ---
            # 1. Regime: Bullish only
            is_bullish_market = (row['spy'] > row['spy_sma200']) and (row['vix'] < 25)

            # 2. Trend: Minervini Alignment
            is_trending = (price > row['sma50'] > row['sma150'] > row['sma200'])

            # 3. Trigger: Breakout
            is_breakout = price > row['donchian_high']

            # --- LOGIC ---
            if self.state == "OUT":
                if is_bullish_market and is_trending and is_breakout:
                    # BUY SIGNAL
                    self.shares = int(self.equity / price)
                    cost = self.shares * price
                    self.equity -= cost # Convert cash to shares
                    self.state = "IN"

                    # Set Initial Stop Loss (2.5 ATR)
                    stop_loss = price - (2.5 * row['atr'])

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "type": "BUY",
                        "price": round(price, 2),
                        "shares": self.shares,
                        "stop": round(stop_loss, 2)
                    })

            elif self.state == "IN":
                # Trailing Stop Update (Donchian Low or keep Initial Stop if higher)
                # We strictly use the "Council's" stop: 2.5 ATR fixed on entry OR 20-day low trail?
                # The user requested "Harden the filters". A trailing stop is safer.
                # Let's use the tighter of: Original Stop OR 20-Day Low
                current_trail = row['donchian_low']
                if current_trail > stop_loss:
                    stop_loss = current_trail

                # EXIT CONDITIONS
                hit_stop = price < stop_loss
                # Hard exit if Trend breaks (Close < 200 SMA)
                trend_break = price < row['sma200']

                if hit_stop or trend_break:
                    # SELL SIGNAL
                    proceeds = self.shares * price
                    self.equity += proceeds
                    self.shares = 0
                    self.state = "OUT"

                    reason = "STOP LOSS" if hit_stop else "TREND BREAK"

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "type": "SELL",
                        "price": round(price, 2),
                        "reason": reason,
                        "equity": round(self.equity, 2)
                    })

        # Finalize (Mark to Market)
        final_equity = self.equity + (self.shares * final_price)
        strat_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100

        return {
            "ticker": self.ticker,
            "period": "2 Years",
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return, 2),
            "trades": len(self.trade_log) // 2, # Round trips
            "win_rate": self._calculate_win_rate(),
            "final_equity": round(final_equity, 2),
            "log": self.trade_log[-5:] # Show last 5 trades
        }

    def _calculate_win_rate(self):
        wins = 0
        losses = 0
        entry_price = 0

        for trade in self.trade_log:
            if trade['type'] == 'BUY':
                entry_price = trade['price']
            elif trade['type'] == 'SELL':
                if trade['price'] > entry_price:
                    wins += 1
                else:
                    losses += 1

        total = wins + losses
        if total == 0: return "0%"
        return f"{round((wins / total) * 100)}%"
