import pandas_ta as ta
from option_auditor.common.screener_utils import ScreeningRunner, DEFAULT_ATR_LENGTH
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.data_utils import _calculate_trend_breakout_date

def screen_bollinger_squeeze(ticker_list: list = None, time_frame: str = "1d", region: str = "us") -> list:
    """
    Screens for TTM Squeeze (Bollinger Bands inside Keltner Channels).
    Squeeze ON = Volatility Compression (Expect Breakout).
    """

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 50: return None

            curr_close = float(df['Close'].iloc[-1])

            # --- CALCULATIONS ---
            # 1. Bollinger Bands (20, 2)
            bb = ta.bbands(df['Close'], length=20, std=2.0)
            if bb is None: return None

            # Columns: BBL, BBM, BBU, Bandwidth, Percent
            bb_lower = bb.iloc[:, 0]
            bb_upper = bb.iloc[:, 2]

            # 2. Keltner Channels (20, 1.5)
            kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
            if kc is None: return None

            # Columns: Lower, Basis, Upper
            kc_lower = kc.iloc[:, 0]
            kc_upper = kc.iloc[:, 2]

            if bb_upper is None or kc_upper is None: return None

            # 3. Squeeze Condition (Most Recent)
            # Squeeze is ON if BB Upper < KC Upper AND BB Lower > KC Lower
            sq_on = (bb_upper.iloc[-1] < kc_upper.iloc[-1]) and (bb_lower.iloc[-1] > kc_lower.iloc[-1])

            if not sq_on: return None

            # 4. Momentum (Close - SMA(20))
            sma_20 = df['Close'].rolling(20).mean().iloc[-1]
            mom = curr_close - sma_20
            mom_color = "green" if mom > 0 else "red"
            signal_desc = "BULLISH SQUEEZE" if mom > 0 else "BEARISH SQUEEZE"

            breakout_date = _calculate_trend_breakout_date(df)

            # Calculate ATR for UI
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (curr_close * 0.01)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            pct_change_1d = 0.0
            if len(df) >= 2:
                prev_c = float(df['Close'].iloc[-2])
                pct_change_1d = ((curr_close - prev_c) / prev_c) * 100

            stop_loss = curr_close - (2*atr) if mom > 0 else curr_close + (2*atr)
            target = curr_close + (3*atr) if mom > 0 else curr_close - (3*atr)

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_close, 2),
                "squeeze_status": "ON",
                "verdict": signal_desc, # UI
                "signal": signal_desc,
                "momentum_val": round(mom, 2),
                "momentum_color": mom_color,
                "pct_change_1d": round(pct_change_1d, 2),
                "atr": round(atr, 2),
                "breakout_date": breakout_date,
                "score": 100, # High priority
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "Setup": signal_desc # Generic UI map
            }

        except Exception as e:
            return None

    return runner.run(strategy)
