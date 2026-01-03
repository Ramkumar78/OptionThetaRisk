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
        self.entry_date = None

    def fetch_data(self):
        try:
            # Fetch 3 years to ensure 200 SMA is ready before the 2-year backtest starts
            symbols = [self.ticker, "SPY", "^VIX"]
            data = yf.download(symbols, period="3y", auto_adjust=True, progress=False)

            if isinstance(data.columns, pd.MultiIndex):
                close = data['Close']
                high = data['High']
                low = data['Low']
                open_price = data['Open'] # Added to fix missing 'open'
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
                'open': get_series(open_price, self.ticker), # Added to fix missing 'open'
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
        df['sma20'] = df['close'].rolling(20).mean()

        # --- Volatility & ATR ---
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # --- MASTER PROTOCOL METRICS ---

        # 1. Relative Strength (RS) vs SPY (Mansfield Proxy)
        # Ratio of Stock/SPY compared to 60 days ago
        rs_ratio = df['close'] / df['spy']
        df['rs_score'] = (rs_ratio / rs_ratio.shift(60)) - 1.0

        # 2. Volatility Contraction Pattern (VCP)
        # Ratio of 10-day StdDev to 50-day StdDev
        vol_10 = df['close'].rolling(10).std()
        vol_50 = df['close'].rolling(50).std()
        # Avoid division by zero
        df['vcp_ratio'] = vol_10 / (vol_50 + 0.0001)

        # 3. Volume Metrics
        df['vol_avg_20'] = df['volume'].rolling(20).mean()

        # Pocket Pivot: Max Down Volume in last 10 days
        is_down = df['close'] < df['close'].shift(1)
        down_vol = df['volume'].where(is_down, 0)
        df['max_down_vol_10'] = down_vol.rolling(10).max().shift(1)

        # --- Donchian Channels (Breakout Confirmation) ---
        df['high_20'] = df['high'].rolling(20).max().shift(1)
        df['low_20'] = df['low'].rolling(20).min().shift(1)
        df['low_10'] = df['low'].rolling(10).min().shift(1)
        df['high_50'] = df['high'].rolling(50).max().shift(1) # Added high_50

        # --- Market Regime ---
        df['spy_sma200'] = df['spy'].rolling(200).mean()

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None or df.empty: return {"error": "No data found"}

        df = self.calculate_indicators(df)

        # --- EXACT SIMULATION WINDOW ---
        start_date = pd.Timestamp.now() - pd.Timedelta(days=730)
        sim_data = df[df.index >= start_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')
        buy_hold_days = (sim_data.index[-1] - sim_data.index[0]).days

        # --- FAIR COMPARISON: BUY & HOLD ---
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

            is_strong_trend = (price > row['sma50'] > row['sma200'])

            # ==============================
            # STRATEGY LOGIC
            # ==============================

            if self.strategy_type == 'master':
                # --- MASTER PROTOCOL (Hybrid) ---

                # A. The "Sniper" Setup (VCP + Edge)
                has_rs_edge = row['rs_score'] > 0.0
                is_squeeze = row['vcp_ratio'] < 0.75 # Relaxed from 0.60 to capture more moves

                vol_spike = row['volume'] > (1.2 * row['vol_avg_20']) # Relaxed Vol Req
                has_demand = vol_spike or (price > row['high_20']) # Breakout is volume enough

                # B. The "Trend" Setup (Don't miss the bus)
                # If we are in a Mega Trend, we take the 20-day breakout even without VCP
                is_mega_trend = (price > row['sma50']) and (row['sma50'] > row['sma200'])
                is_breakout = price > row['high_20']

                # ENTRY TRIGGER:
                # 1. Perfect VCP Setup OR
                # 2. Strong Trend Breakout (Participation)
                if (has_rs_edge and is_squeeze and has_demand) or (is_mega_trend and is_breakout):
                    buy_signal = True

                # EXIT LOGIC:
                # 1. Trend Break: Close below SMA 50
                if price < row['sma50']:
                    sell_signal = True
                    current_stop_reason = "TREND BREAK (<50)"

            elif self.strategy_type == 'turtle':
                if price > row['high_20']: buy_signal = True
                if self.state == "IN" and price < row['low_10']:
                    sell_signal = True
                    current_stop_reason = "10d LOW EXIT"

            elif self.strategy_type == 'isa':
                is_breakout_50 = row['close'] > row['high_50'] # Use row['high_50'] from indicators
                is_isa_reentry = (price > row['sma50']) and (price > row['sma200'])
                if (price > row['sma200']) and (is_breakout_50 or is_isa_reentry): buy_signal = True
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
                self.entry_date = date

                # Set Initial Stop (Wider for Master to avoid noise)
                if self.strategy_type == 'master':
                    # 3.0 ATR allows for normal volatility without shaking us out
                    stop_loss = price - (3.0 * row['atr'])
                elif self.strategy_type == 'isa':
                    stop_loss = row['low_20']
                else:
                    stop_loss = row['low_10']

                self.trade_log.append({
                    "date": date.strftime('%Y-%m-%d'), "type": "BUY",
                    "price": round(price, 2), "stop": round(stop_loss, 2),
                    "days": "-"
                })

            elif self.state == "IN":
                # Trailing Stop Management
                if self.strategy_type == 'master':
                    # Hybrid Trail: Donchian 20 Low (Classic) or 3 ATR
                    # This lets the stock "breathe"
                    trail_stop = max(row['low_20'], price - (3.0 * row['atr']))
                    if trail_stop > stop_loss: stop_loss = trail_stop

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

                    days_held = (date - self.entry_date).days
                    reason = current_stop_reason if sell_signal else "STOP HIT"

                    self.trade_log.append({
                        "date": date.strftime('%Y-%m-%d'), "type": "SELL",
                        "price": round(price, 2), "reason": reason,
                        "equity": round(self.equity, 0),
                        "days": days_held
                    })

        final_eq = self.equity + (self.shares * final_price)
        strat_return = ((final_eq - self.initial_capital) / self.initial_capital) * 100

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
