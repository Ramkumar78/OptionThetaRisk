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
        self.entry_date = None  # Track entry date for duration calc

    def fetch_data(self):
        try:
            # Fetch 3 years to ensure 200 SMA is ready before the 2-year backtest starts
            symbols = [self.ticker, "SPY", "^VIX"]
            data = yf.download(symbols, period="3y", auto_adjust=True, progress=False)

            if isinstance(data.columns, pd.MultiIndex):
                close = data['Close']
                high = data['High']
                low = data['Low']
                vol = data['Volume']
            else:
                return None

            def get_series(df, sym):
                if sym in df.columns: return df[sym]
                return df.iloc[:, 0]

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
        # --- Trend Moving Averages ---
        df['sma200'] = df['close'].rolling(200).mean()
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma150'] = df['close'].rolling(150).mean()
        df['sma20'] = df['close'].rolling(20).mean() # For fast re-entry

        # --- Volatility ---
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # --- Market Regime ---
        df['spy_sma200'] = df['spy'].rolling(200).mean()

        # --- Breakout Channels ---
        # Donchian Channels (shifted by 1 to represent "Yesterday's" levels)
        df['high_20'] = df['high'].rolling(20).max().shift(1)
        df['low_10'] = df['low'].rolling(10).min().shift(1)
        df['high_50'] = df['high'].rolling(50).max().shift(1)
        df['low_20'] = df['low'].rolling(20).min().shift(1)

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None or df.empty: return {"error": "No data found"}

        df = self.calculate_indicators(df)

        # --- EXACT SIMULATION WINDOW ---
        # We start exactly 2 years ago
        start_date = pd.Timestamp.now() - pd.Timedelta(days=730)
        sim_data = df[df.index >= start_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        # Get Actual Start/End Dates for Report
        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')

        # Calculate Buy & Hold Duration
        buy_hold_days = (sim_data.index[-1] - sim_data.index[0]).days

        # --- FAIR COMPARISON: BUY & HOLD ---
        # Invest 100% of capital on Day 1 Open/Close
        initial_price = sim_data['close'].iloc[0]
        final_price = sim_data['close'].iloc[-1]

        bnh_shares = int(self.initial_capital / initial_price)
        bnh_final_value = self.initial_capital - (bnh_shares * initial_price) + (bnh_shares * final_price)
        bnh_return = ((bnh_final_value - self.initial_capital) / self.initial_capital) * 100

        # --- STRATEGY LOOP ---
        stop_loss = 0.0

        for date, row in sim_data.iterrows():
            price = row['close']
            buy_signal = False
            sell_signal = False
            current_stop_reason = "STOP"

            # --- COMMON CONDITIONS ---
            is_bullish_market = (row['spy'] > row['spy_sma200']) and (row['vix'] < 25)
            is_strong_trend = (price > row['sma50'] > row['sma150'] > row['sma200'])

            # ==============================
            # STRATEGY LOGIC
            # ==============================

            if self.strategy_type == 'master':
                # 1. Breakout Entry: New 20 Day High
                is_breakout = price > row['high_20']

                # 2. Re-Entry Protocol: If Trend is Intact (>50, >150, >200) but we are flat,
                #    enter on SMA 20 Cross instead of waiting for High 20.
                is_reentry = (price > row['sma20']) and is_strong_trend

                # Combined Buy Logic
                if is_bullish_market and (is_breakout or is_reentry) and is_strong_trend:
                    buy_signal = True

                # Exit Logic: Trend Break or Stop
                if price < row['sma200']:
                    sell_signal = True
                    current_stop_reason = "TREND BREAK (<200)"

            elif self.strategy_type == 'turtle':
                if price > row['high_20']:
                    buy_signal = True

                if self.state == "IN" and price < row['low_10']:
                    sell_signal = True
                    current_stop_reason = "10d LOW EXIT"

            elif self.strategy_type == 'isa':
                is_breakout_50 = price > row['high_50']
                is_isa_reentry = (price > row['sma50']) and (price > row['sma200'])

                if (price > row['sma200']) and (is_breakout_50 or is_isa_reentry):
                    buy_signal = True

                if self.state == "IN" and price < row['low_20']:
                    sell_signal = True
                    current_stop_reason = "20d LOW EXIT"

            # ==============================
            # EXECUTION
            # ==============================

            if self.state == "OUT" and buy_signal:
                self.shares = int(self.equity / price)
                self.equity -= (self.shares * price)
                self.state = "IN"
                self.entry_date = date # Capture Entry Date

                # Set Initial Stop
                if self.strategy_type == 'master':
                    stop_loss = price - (2.5 * row['atr'])
                elif self.strategy_type == 'isa':
                    stop_loss = row['low_20']
                else: # Turtle
                    stop_loss = row['low_10']

                self.trade_log.append({
                    "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                    "price": round(price, 2), "stop": round(stop_loss, 2),
                    "days": "-"
                })

            elif self.state == "IN":
                # Trailing Stop Management
                if self.strategy_type == 'master':
                    atr_stop = price - (2.5 * row['atr'])
                    donchian_stop = row['low_20']
                    new_stop = max(atr_stop, donchian_stop)
                    if new_stop > stop_loss: stop_loss = new_stop

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

                    # Calculate Days Held
                    days_held = (date - self.entry_date).days

                    reason = current_stop_reason if sell_signal else "STOP HIT"

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'), "type": "SELL",
                        "price": round(price, 2), "reason": reason,
                        "equity": round(self.equity, 0),
                        "days": days_held
                    })

        # Final Valuation
        final_eq = self.equity + (self.shares * final_price)
        strat_return = ((final_eq - self.initial_capital) / self.initial_capital) * 100

        # Calculate Average Days Held
        sell_trades = [t['days'] for t in self.trade_log if t['type'] == 'SELL' and isinstance(t['days'], int)]
        avg_days_held = round(sum(sell_trades) / len(sell_trades)) if sell_trades else 0

        return {
            "ticker": self.ticker,
            "strategy": self.strategy_type.upper(),
            "start_date": actual_start_str,
            "end_date": actual_end_str,
            "strategy_return": round(strat_return, 2),
            "buy_hold_return": round(bnh_return, 2),
            "buy_hold_days": buy_hold_days,
            "avg_days_held": avg_days_held,
            "trades": len(self.trade_log) // 2,
            "win_rate": self._calculate_win_rate(),
            "final_equity": round(final_eq, 2),
            "log": self.trade_log
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
