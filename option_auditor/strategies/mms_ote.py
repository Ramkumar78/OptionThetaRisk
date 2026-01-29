import logging
import pandas_ta as ta
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    DEFAULT_ATR_LENGTH
)
from option_auditor.common.constants import TICKER_NAMES
from option_auditor.common.data_utils import _calculate_trend_breakout_date
from option_auditor.strategies.liquidity import _identify_swings, _detect_fvgs

logger = logging.getLogger(__name__)

def screen_mms_ote_setups(ticker_list: list = None, time_frame: str = "1h", region: str = "us", check_mode: bool = False) -> list:
    """
    Screens for ICT Market Maker Models + OTE (Optimal Trade Entry).
    """
    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region, check_mode=check_mode)

    def strategy(ticker, df):
        try:
            min_length = 50 if check_mode else 50
            if len(df) < min_length: return None

            curr_close = float(df['Close'].iloc[-1])

            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            current_atr = df['ATR'].iloc[-1] if 'ATR' in df.columns and not df['ATR'].empty else 0.0
            volatility_pct = (current_atr / curr_close * 100) if curr_close > 0 else 0.0

            df = _identify_swings(df, lookback=3)

            last_swings_high = df[df['Swing_High'].notna()]
            last_swings_low = df[df['Swing_Low'].notna()]

            if last_swings_high.empty or last_swings_low.empty:
                return None

            signal = "WAIT"
            setup_details = {}

            peak_idx = df['High'].iloc[-40:].idxmax()
            peak_high = df.loc[peak_idx, 'High']

            after_peak = df.loc[peak_idx:]
            if len(after_peak) < 3: return None

            valley_idx = after_peak['Low'].idxmin()
            valley_low = df.loc[valley_idx, 'Low']

            range_size = peak_high - valley_low
            fib_62 = peak_high - (range_size * 0.618)
            fib_79 = peak_high - (range_size * 0.79)

            fvgs = _detect_fvgs(after_peak)
            bearish_fvgs = [f for f in fvgs if f['type'] == "BEARISH"]
            has_fvg = len(bearish_fvgs) > 0

            if has_fvg and (fib_79 <= curr_close <= fib_62):
                 before_peak = df.loc[:peak_idx].iloc[:-1]
                 if not before_peak.empty:
                     prev_swing_lows = before_peak[before_peak['Swing_Low'].notna()]
                     if not prev_swing_lows.empty:
                         last_structural_low = prev_swing_lows['Low'].iloc[-1]

                         if valley_low < last_structural_low:
                             signal = "🐻 BEARISH OTE (Sell)"
                             setup_details = {
                                 "stop": peak_high,
                                 "entry_zone": f"{fib_62:.2f} - {fib_79:.2f}",
                                 "target": valley_low - range_size # -1.0 extension
                             }

            if signal == "WAIT":
                trough_idx = df['Low'].iloc[-40:].idxmin()
                trough_low = df.loc[trough_idx, 'Low']

                after_trough = df.loc[trough_idx:]

                if len(after_trough) >= 5:
                    peak_up_idx = after_trough['High'].idxmax()
                    peak_up_high = df.loc[peak_up_idx, 'High']

                    if peak_up_high > trough_low and curr_close < peak_up_high:

                        range_up = peak_up_high - trough_low
                        fib_62_up = trough_low + (range_up * 0.618)
                        fib_79_up = trough_low + (range_up * 0.79)

                        retracement_pct = (peak_up_high - curr_close) / range_up

                        if 0.618 <= retracement_pct <= 0.79:
                             before_trough = df.loc[:trough_idx].iloc[:-1]
                             valid_mss = False

                             if not before_trough.empty:
                                 last_pre_crash_high = before_trough['High'].tail(10).max()
                                 if peak_up_high > last_pre_crash_high:
                                     valid_mss = True

                             if valid_mss:
                                 signal = "🐂 BULLISH OTE (Buy)"
                                 setup_details = {
                                     "stop": trough_low,
                                     "entry_zone": f"{fib_62_up:.2f} - {fib_79_up:.2f}",
                                     "target": peak_up_high + range_up
                                 }

            breakout_date = _calculate_trend_breakout_date(df)

            high_52wk = df['High'].rolling(252).max().iloc[-1] if len(df) >= 252 else df['High'].max()
            low_52wk = df['Low'].rolling(252).min().iloc[-1] if len(df) >= 252 else df['Low'].min()

            if signal != "WAIT" or check_mode:
                pct_change_1d = None
                if len(df) >= 2:
                    try:
                        prev_close_px = float(df['Close'].iloc[-2])
                        pct_change_1d = ((curr_close - prev_close_px) / prev_close_px) * 100
                    except Exception as e:
                        logger.debug(f"Pct change calc failed: {e}")

                base_ticker = ticker.split('.')[0]
                company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

                return {
                    "ticker": ticker,
                    "company_name": company_name,
                    "price": curr_close,
                    "pct_change_1d": pct_change_1d,
                    "signal": signal,
                    "stop_loss": setup_details.get('stop', 0.0),
                    "ote_zone": setup_details.get('entry_zone', "N/A"),
                    "target": setup_details.get('target', 0.0),
                    "fvg_detected": "Yes",
                    "atr_value": round(current_atr, 2),
                    "volatility_pct": round(volatility_pct, 2),
                    "breakout_date": breakout_date,
                    "atr": round(current_atr, 2),
                    "52_week_high": round(high_52wk, 2) if high_52wk else None,
                    "52_week_low": round(low_52wk, 2) if low_52wk else None,
                    "sector_change": pct_change_1d
                }
        except Exception as e:
            logger.error(f"Error processing OTE for {ticker}: {e}")
            return None
        return None

    return runner.run(strategy)
