import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
from option_auditor.unified_screener import analyze_ticker_hardened, get_market_regime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedBacktester")

class UnifiedBacktester:
    def __init__(self, ticker, strategy_type="grandmaster", initial_capital=10000.0):
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
                try:
                    close = data['Close']
                    high = data['High']
                    low = data['Low']
                    open_price = data['Open']
                    vol = data['Volume']
                except KeyError:
                    # yfinance 0.2.x structure variations
                     return None
            else:
                return None

            def get_series(df, sym):
                if sym in df.columns: return df[sym]
                # Fallback if single level or other issue
                return pd.Series(dtype=float)

            df = pd.DataFrame({
                'close': get_series(close, self.ticker),
                'high': get_series(high, self.ticker),
                'low': get_series(low, self.ticker),
                'open': get_series(open_price, self.ticker),
                'volume': get_series(vol, self.ticker),
                'spy': get_series(close, 'SPY'),
                'vix': get_series(close, '^VIX')
            }).dropna()

            # Capitalize columns to match unified_screener expectations (Close, High, Low...)
            df.columns = [c.capitalize() for c in df.columns] # Close, High, Low, Open, Volume, Spy, Vix

            return df
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return None

    def calculate_indicators(self, df):
        # Additional indicators for Turtle/Legacy strategies if needed
        # Unified Screener calculates its own, but we can pre-calc helpers

        # --- Trend Moving Averages ---
        df['sma200'] = df['Close'].rolling(200).mean()
        df['sma50'] = df['Close'].rolling(50).mean()
        df['sma150'] = df['Close'].rolling(150).mean()
        df['sma20'] = df['Close'].rolling(20).mean()

        # --- Volatility & ATR ---
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        # --- Donchian Channels (Legacy) ---
        df['high_20'] = df['High'].rolling(20).max().shift(1)
        df['high_10'] = df['High'].rolling(10).max().shift(1)
        df['low_20'] = df['Low'].rolling(20).min().shift(1)
        df['low_10'] = df['Low'].rolling(10).min().shift(1)
        df['high_50'] = df['High'].rolling(50).max().shift(1)

        # Regime Indicators
        df['spy_sma200'] = df['Spy'].rolling(200).mean()

        return df.dropna()

    def run(self):
        df = self.fetch_data()
        if df is None or df.empty: return {"error": "No data found"}

        df = self.calculate_indicators(df)

        # --- EXACT SIMULATION WINDOW ---
        start_date = pd.Timestamp.now() - pd.Timedelta(days=730)
        # If simulation data is older (e.g. testing with fixed dates), this might result in empty.
        # Fallback for testing: if df ends before start_date, use entire df
        if df.index[-1] < start_date:
             sim_data = df.copy()
        else:
             sim_data = df[df.index >= start_date].copy()

        if sim_data.empty: return {"error": "Not enough history"}

        actual_start_str = sim_data.index[0].strftime('%Y-%m-%d')
        actual_end_str = sim_data.index[-1].strftime('%Y-%m-%d')
        buy_hold_days = (sim_data.index[-1] - sim_data.index[0]).days

        # --- FAIR COMPARISON: BUY & HOLD ---
        initial_price = sim_data['Close'].iloc[0]
        final_price = sim_data['Close'].iloc[-1]
        bnh_shares = int(self.initial_capital / initial_price)
        bnh_final_value = self.initial_capital - (bnh_shares * initial_price) + (bnh_shares * final_price)
        bnh_return = ((bnh_final_value - self.initial_capital) / self.initial_capital) * 100

        # --- STRATEGY LOOP ---
        stop_loss = 0.0

        for date, row in sim_data.iterrows():
            price = row['Close']
            buy_signal = False
            sell_signal = False
            current_stop_reason = "STOP"

            # Dynamic Regime Check
            # We reconstruct the regime logic from unified_screener using historical columns
            regime = "RED"
            spy_price = row['Spy']
            spy_sma = row['spy_sma200']
            vix_price = row['Vix']

            if spy_price > spy_sma and vix_price < 20:
                regime = "GREEN"
            elif spy_price > spy_sma and vix_price < 28:
                regime = "YELLOW"

            # --- STRATEGY LOGIC ---

            if self.strategy_type in ['grandmaster', 'council', 'master']:
                # Simulate "Grandmaster" Logic
                # We need to pass a slice of DF up to this date to mimic the screener seeing only past data
                # Optimization: We already have indicators in 'row'. We can implement simplified logic
                # or slice. Slicing inside loop is slow (O(N^2)).
                # Let's use indicators calculated in `calculate_indicators` which respect time (rolling).

                # REIMPLEMENT LOGIC FROM unified_screener.analyze_ticker_hardened

                # 1. Regime Filter
                if regime == "RED":
                    # Hard Exit if holding
                    if self.state == "IN":
                        sell_signal = True
                        current_stop_reason = "REGIME CHANGE (RED)"
                    # No new buys
                    buy_signal = False

                else:
                    # 2. Technical Metrics (Already in row)
                    sma50 = row['sma50']
                    sma200 = row['sma200']
                    # rvol approx (using 20 day avg vol)
                    avg_vol_20 = sim_data.loc[:date]['Volume'].tail(20).mean()
                    rvol = row['Volume'] / avg_vol_20 if avg_vol_20 > 0 else 0

                    # 3. ISA Mode Logic

                    # Trend Template
                    is_trend = (price > sma200) and (price > sma50) and (sma50 > sma200)

                    # 52w High/Low (Need history)
                    # We can use rolling max/min on the slice
                    # Optimization: pre-calculate in indicators?
                    # Let's assume we use pre-calcs if possible or simplified

                    # Trigger: VCP Breakout (High of last 20 days)
                    high_20d = row['high_20']
                    breakout = (price > high_20d) and (rvol > 1.2)

                    if is_trend and breakout:
                        buy_signal = True
                        # Stop Loss logic handled in Execution block

                    # Exit Logic for ISA
                    # unified_screener uses strict stop loss at purchase.
                    # Does it have a trailing exit?
                    # "Trailing Stop (20-Day Low)" is mentioned in README for ISA.
                    # unified_screener.analyze_ticker_hardened sets initial stop at 2.5*ATR.

                    if self.state == "IN":
                        # Trailing Stop: 20 Day Low
                        trail_stop = row['low_20']
                        if price < trail_stop:
                            sell_signal = True
                            current_stop_reason = "TRAILING STOP (20d Low)"

            elif self.strategy_type == 'turtle':
                if price > row['high_20']: buy_signal = True
                if self.state == "IN" and price < row['low_10']:
                    sell_signal = True
                    current_stop_reason = "10d LOW EXIT"

            elif self.strategy_type == 'isa': # Legacy ISA
                is_breakout_50 = row['Close'] > row['high_50']
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

                # Set Initial Stop
                if self.strategy_type in ['grandmaster', 'council', 'master']:
                    # 2.5 ATR Initial
                    stop_loss = price - (2.5 * row['atr'])
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
                # Trailing Stop Management (For Grandmaster)
                # We handled SELL Signal generation above.
                # Here we check the hard initial stop.

                hit_stop = price < stop_loss

                if hit_stop or sell_signal:
                    proceeds = self.shares * price
                    self.equity += proceeds
                    self.shares = 0
                    self.state = "OUT"

                    days_held = (date - self.entry_date).days
                    reason = current_stop_reason if sell_signal else "INITIAL STOP HIT"

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
