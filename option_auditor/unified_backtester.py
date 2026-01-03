import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedBacktester")

class UnifiedBacktester:
    def __init__(self, ticker, strategy_type="master", initial_capital=10000.0):
        self.ticker = ticker.upper()
        self.strategy_type = strategy_type
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.shares = 0
        self.state = "OUT"
        self.trade_log = []

    def fetch_data(self):
        try:
            # We need SPY/VIX for Master/ISA regimes, just Ticker for Turtle
            symbols = [self.ticker, "SPY", "^VIX"]
            data = yf.download(symbols, period="3y", auto_adjust=True, progress=False)

            # Handle MultiIndex vs Single Index
            if isinstance(data.columns, pd.MultiIndex):
                close = data['Close']
                high = data['High']
                low = data['Low']
                vol = data['Volume']
            else:
                return None

            # Safe extraction
            def get_series(df, sym):
                if sym in df.columns: return df[sym]
                return df.iloc[:, 0] # Fallback

            df = pd.DataFrame({
                'close': get_series(close, self.ticker),
                'high': get_series(high, self.ticker),
                'low': get_series(low, self.ticker),
                'volume': get_series(vol, self.ticker),
                'spy': get_series(close, 'SPY'),
                'vix': get_series(close, '^VIX')
            }).dropna()

            return df
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return None

    def calculate_indicators(self, df):
        # --- Common Indicators ---
        df['sma200'] = df['close'].rolling(200).mean()
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma150'] = df['close'].rolling(150).mean()
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # --- Market Regime ---
        df['spy_sma200'] = df['spy'].rolling(200).mean()

        # --- Strategy Specifics ---

        # 1. Turtle (20 High / 10 Low)
        df['high_20'] = df['high'].rolling(20).max().shift(1)
        df['low_10'] = df['low'].rolling(10).min().shift(1)

        # 2. ISA (50 High / 20 Low)
        df['high_50'] = df['high'].rolling(50).max().shift(1)
        df['low_20'] = df['low'].rolling(20).min().shift(1)

        # 3. Master (Minervini Trend) is covered by SMAs above

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None or df.empty: return {"error": "No data found"}

        df = self.calculate_indicators(df)

        # Simulation Window (Last 2 Years)
        start_date = pd.Timestamp.now() - pd.DateOffset(years=2)
        sim_data = df[df.index >= start_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        # Buy & Hold Logic
        initial_price = sim_data['close'].iloc[0]
        final_price = sim_data['close'].iloc[-1]
        bnh_return = ((final_price - initial_price) / initial_price) * 100

        stop_loss = 0.0

        for date, row in sim_data.iterrows():
            price = row['close']
            buy_signal = False
            sell_signal = False
            current_stop_reason = "STOP"

            # ==============================
            # STRATEGY LOGIC SWITCH
            # ==============================

            if self.strategy_type == 'master':
                # RULES: Bullish Market + Minervini Trend + 20d Breakout
                is_bullish_market = (row['spy'] > row['spy_sma200']) and (row['vix'] < 25)
                is_trending = (price > row['sma50'] > row['sma150'] > row['sma200'])
                is_breakout = price > row['high_20']

                if is_bullish_market and is_trending and is_breakout:
                    buy_signal = True
                    # Master uses 2.5 ATR trailing or Low 20? Let's use 2.5 ATR Fixed on entry
                    # Actually user asked for "Pro use", usually trailing.
                    # We will calculate stop dynamically below.

                # Exit: Trend Break or Stop
                if price < row['sma200']: sell_signal = True; current_stop_reason = "TREND BREAK"

            elif self.strategy_type == 'turtle':
                # RULES: Price > 20d High. Exit Price < 10d Low.
                if price > row['high_20']:
                    buy_signal = True

                if self.state == "IN" and price < row['low_10']:
                    sell_signal = True
                    current_stop_reason = "10d LOW EXIT"

            elif self.strategy_type == 'isa':
                # RULES: Price > 200 SMA + Price > 50d High. Exit < 20d Low.
                trend_ok = price > row['sma200']
                if trend_ok and price > row['high_50']:
                    buy_signal = True

                if self.state == "IN" and price < row['low_20']:
                    sell_signal = True
                    current_stop_reason = "20d LOW EXIT"

            # ==============================
            # EXECUTION ENGINE
            # ==============================

            if self.state == "OUT" and buy_signal:
                self.shares = int(self.equity / price)
                self.equity -= (self.shares * price)
                self.state = "IN"

                # Initial Stop Setting
                if self.strategy_type == 'master':
                    stop_loss = price - (2.5 * row['atr'])
                elif self.strategy_type == 'isa':
                    stop_loss = row['low_20']
                else: # Turtle
                    stop_loss = row['low_10']

                self.trade_log.append({
                    "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                    "price": round(price, 2), "stop": round(stop_loss, 2)
                })

            elif self.state == "IN":
                # Trailing Stop Management
                if self.strategy_type == 'master':
                    # Trail stop up if price moves up (Donchian 20 floor)
                    if row['low_20'] > stop_loss: stop_loss = row['low_20']
                elif self.strategy_type == 'isa':
                    stop_loss = row['low_20']
                elif self.strategy_type == 'turtle':
                    stop_loss = row['low_10']

                # Check Exits
                hit_stop = price < stop_loss

                if hit_stop or sell_signal:
                    proceeds = self.shares * price
                    self.equity += proceeds
                    self.shares = 0
                    self.state = "OUT"

                    reason = current_stop_reason if sell_signal else "STOP HIT"

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'), "type": "SELL",
                        "price": round(price, 2), "reason": reason,
                        "equity": round(self.equity, 0)
                    })

        # Final Valuation
        final_eq = self.equity + (self.shares * final_price)
        strat_return = ((final_eq - self.initial_capital) / self.initial_capital) * 100

        return {
            "ticker": self.ticker,
            "strategy": self.strategy_type.upper(),
            "period": "2 Years",
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return, 2),
            "trades": len(self.trade_log) // 2,
            "win_rate": self._calculate_win_rate(),
            "final_equity": round(final_eq, 2),
            "log": self.trade_log[-5:]
        }

    def _calculate_win_rate(self):
        wins = 0; losses = 0; entry = 0
        for t in self.trade_log:
            if t['type'] == 'BUY': entry = t['price']
            if t['type'] == 'SELL':
                if t['price'] > entry: wins += 1
                else: losses += 1
        total = wins + losses
        if total == 0: return "0%"
        return f"{round((wins/total)*100)}%"
