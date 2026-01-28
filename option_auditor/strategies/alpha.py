import pandas_ta as ta
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    DEFAULT_ATR_LENGTH,
    DEFAULT_SMA_FAST,
    DEFAULT_SMA_SLOW
)
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.data_utils import _calculate_trend_breakout_date

def screen_alpha_101(ticker_list: list = None, region: str = "us", time_frame: str = "1d") -> list:
    """
    Implements Alpha#101: ((close - open) / ((high - low) + .001))
    Paper Source: 101 Formulaic Alphas (Kakushadze, 2015)
    Logic: Delay-1 Momentum. If stock runs up intraday (Close >> Open), go Long.
    """
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 5: return None

            # --- ALPHA #101 CALCULATION ---
            # Formula: ((close - open) / ((high - low) + 0.001))
            # We use the most recent completed day
            curr_row = df.iloc[-1]

            c = float(curr_row['Close'])
            o = float(curr_row['Open'])
            h = float(curr_row['High'])
            l = float(curr_row['Low'])

            denom = (h - l) + 0.001
            alpha_val = (c - o) / denom

            # --- SIGNAL LOGIC ---
            # Thresholds: > 0.5 implies strong closing strength (Marubozu-like)
            signal = "WAIT"
            color = "gray"

            if alpha_val > 0.5:
                signal = "🚀 STRONG BUY (Alpha > 0.5)"
                color = "green"
            elif alpha_val > 0.25:
                signal = "📈 BULLISH MOMENTUM"
                color = "blue"
            elif alpha_val < -0.5:
                signal = "📉 STRONG SELL (Alpha < -0.5)"
                color = "red"
            elif alpha_val < -0.25:
                signal = "⚠️ BEARISH PRESSURE"
                color = "orange"

            # Filter: Only show active signals to reduce noise?
            if abs(alpha_val) < 0.25:
                return None

            # --- METRICS ---
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (c * 0.01)

            # Risk Management (Paper suggests holding 1-6 days)
            # We use a tight stop below the low of the signal day
            stop_loss = l - (atr * 0.5) if alpha_val > 0 else h + (atr * 0.5)
            target = c + (atr * 2) if alpha_val > 0 else c - (atr * 2)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            pct_change_1d = 0.0
            if len(df) >= 2:
                prev_c = float(df['Close'].iloc[-2])
                pct_change_1d = ((c - prev_c) / prev_c) * 100

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(c, 2),
                "alpha_101": round(alpha_val, 4),
                "signal": signal,
                "verdict": signal, # Alias for UI
                "pct_change_1d": pct_change_1d,
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr": round(atr, 2),
                "score": round(abs(alpha_val) * 100, 1), # Sort by intensity
                "breakout_date": _calculate_trend_breakout_date(df)
            }

        except Exception as e:
            return None

    results = runner.run(strategy)
    # Sort by Alpha Value (Positive/Strongest first)
    results.sort(key=lambda x: x['alpha_101'], reverse=True)
    return results

def screen_my_strategy(ticker_list: list = None, region: str = "us") -> list:
    """
    My Strategy: Combines ISA Trend (Macro) + Alpha #101 (Micro).
    1. Filter: Price > 200 SMA & Price > 50 SMA (Trend).
    2. Trigger: Alpha #101 > 0.5 (Momentum).
    """
    # 2y period for 200 SMA
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame="1d", region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 200: return None # Need 200 SMA

            # --- 1. MACRO DATA (ISA TREND) ---
            curr_close = float(df['Close'].iloc[-1])
            curr_open = float(df['Open'].iloc[-1])
            curr_high = float(df['High'].iloc[-1])
            curr_low = float(df['Low'].iloc[-1])

            sma_50 = df['Close'].rolling(DEFAULT_SMA_FAST).mean().iloc[-1]
            sma_200 = df['Close'].rolling(DEFAULT_SMA_SLOW).mean().iloc[-1]

            # 50-Day High (Breakout Level)
            high_50 = df['High'].rolling(DEFAULT_SMA_FAST).max().shift(1).iloc[-1]

            # ATR (Volatility)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (curr_close * 0.01)

            # Trend Check
            is_trend_up = (curr_close > sma_200) and (curr_close > sma_50)

            if not is_trend_up:
                return None # Strict Filter: Only Bullish Trends

            # --- 2. MICRO DATA (ALPHA #101) ---
            # Formula: (Close - Open) / ((High - Low) + 0.001)
            denom = (curr_high - curr_low) + 0.001
            alpha_val = (curr_close - curr_open) / denom

            # --- 3. COMBINED VERDICT ---
            signal = "WAIT"
            color = "gray"
            score = 50

            # Breakout Check
            dist_to_breakout = (curr_close - high_50) / high_50

            if alpha_val > 0.5:
                # Strong Intraday buying in a Bull Trend
                signal = "🚀 SNIPER ENTRY (Alpha > 0.5)"
                color = "green"
                score = 95
            elif alpha_val < -0.5:
                # Strong Selling in a Bull Trend (Pullback or Exit?)
                signal = "⚠️ SELLING PRESSURE"
                color = "orange"
                score = 40
            elif curr_close > high_50:
                 signal = "✅ BREAKOUT (Trend)"
                 color = "blue"
                 score = 80
            elif dist_to_breakout > -0.05:
                 signal = "👀 WATCH (Near Breakout)"
                 color = "yellow"
                 score = 60

            # --- 4. RISK MANAGEMENT (Populate Fields) ---
            if alpha_val > 0.5:
                stop_loss = curr_low - (atr * 0.5)
            else:
                stop_loss = curr_close - (3 * atr)

            risk = curr_close - stop_loss
            target = curr_close + (risk * 2) if risk > 0 else curr_close + (5 * atr)

            breakout_date = _calculate_trend_breakout_date(df)
            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            if signal == "WAIT": return None

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_close, 2),
                "verdict": signal, # UI uses this for main badge
                "signal": signal,
                "alpha_101": round(alpha_val, 2),
                "breakout_level": round(high_50, 2), # 50-Day High
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr_value": round(atr, 2),
                "breakout_date": breakout_date,
                "score": score,
                "color": color, # For UI Badge
                # Extra stats
                "pct_change_1d": round(((curr_close - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100, 2)
            }

        except Exception as e:
            return None

    results = runner.run(strategy)
    # Sort by Score (Best Setups first)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results
