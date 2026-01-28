import pandas as pd
import logging
from option_auditor.common.screener_utils import (
    ScreeningRunner,
    _calculate_trend_breakout_date,
    DEFAULT_ATR_LENGTH
)
from option_auditor.common.constants import TICKER_NAMES

logger = logging.getLogger(__name__)

def _identify_swings(df: pd.DataFrame, lookback: int = 2) -> pd.DataFrame:
    """
    Identifies fractal Swing Highs and Swing Lows.
    A swing high is a high surrounded by lower highs on both sides.
    """
    df = df.copy()
    # Swing High
    df['Swing_High'] = df['High'][
        (df['High'] > df['High'].shift(1)) &
        (df['High'] > df['High'].shift(-1))
    ]
    # Swing Low
    df['Swing_Low'] = df['Low'][
        (df['Low'] < df['Low'].shift(1)) &
        (df['Low'] < df['Low'].shift(-1))
    ]
    return df

def _detect_fvgs(df: pd.DataFrame) -> list:
    """
    Detects unmitigated Fair Value Gaps (FVGs) in the last 20 candles.
    Returns a list of dicts: {'type': 'bull/bear', 'top': float, 'bottom': float, 'index': datetime}
    """
    fvgs = []

    if len(df) < 3:
        return []

    highs = df['High'].values
    lows = df['Low'].values
    times = df.index

    # Check last 30 candles
    start_idx = max(2, len(df) - 30)

    for i in range(start_idx, len(df)):
        if lows[i-2] > highs[i]:
            gap_size = lows[i-2] - highs[i]
            if gap_size > (highs[i] * 0.0002):
                fvgs.append({
                    "type": "BEARISH",
                    "top": lows[i-2],
                    "bottom": highs[i],
                    "ts": times[i-1]
                })

        if highs[i-2] < lows[i]:
            gap_size = lows[i] - highs[i-2]
            if gap_size > (lows[i] * 0.0002):
                fvgs.append({
                    "type": "BULLISH",
                    "top": lows[i],
                    "bottom": highs[i-2],
                    "ts": times[i-1]
                })
    return fvgs

def screen_liquidity_grabs(ticker_list: list = None, time_frame: str = "1h", region: str = "us") -> list:
    """
    Screens for Liquidity Grabs (Sweeps) of recent Swing Highs/Lows.
    """
    try:
        import pandas_ta as ta
    except ImportError:
        logger.error("pandas_ta not installed")
        return []

    runner = ScreeningRunner(ticker_list=ticker_list, time_frame=time_frame, region=region)

    def strategy(ticker, df):
        try:
            if len(df) < 50: return None

            # Identify Swings
            df_swings = _identify_swings(df, lookback=3)

            # Current Candle
            curr = df.iloc[-1]
            curr_c = float(curr['Close'])
            curr_h = float(curr['High'])
            curr_l = float(curr['Low'])

            # Previous Swings (excluding current candle)
            history = df_swings.iloc[:-1].tail(50)

            swing_highs = history[history['Swing_High'].notna()]['Swing_High']
            swing_lows = history[history['Swing_Low'].notna()]['Swing_Low']

            signal = "WAIT"
            verdict_color = "gray"
            sweep_level = 0.0
            displacement_pct = 0.0

            # BULLISH SWEEP CHECK
            if not swing_lows.empty:
                breached_lows = swing_lows[swing_lows > curr_l] # Lows that are higher than current low (so we dipped below them)

                if not breached_lows.empty:
                    # Check if we closed ABOVE them (Rejection)
                    valid_sweeps = breached_lows[breached_lows < curr_c]

                    if not valid_sweeps.empty:
                        sweep_level = valid_sweeps.min()
                        signal = "🐂 BULLISH SWEEP"
                        verdict_color = "green"
                        displacement_pct = ((curr_c - sweep_level) / sweep_level) * 100

            # BEARISH SWEEP CHECK
            if signal == "WAIT" and not swing_highs.empty:
                breached_highs = swing_highs[swing_highs < curr_h] # Highs lower than current high (so we spiked above)

                if not breached_highs.empty:
                    # Check if we closed BELOW them (Rejection)
                    valid_sweeps = breached_highs[breached_highs > curr_c]

                    if not valid_sweeps.empty:
                        sweep_level = valid_sweeps.max()
                        signal = "🐻 BEARISH SWEEP"
                        verdict_color = "red"
                        displacement_pct = ((curr_c - sweep_level) / sweep_level) * 100

            if signal == "WAIT": return None

            # ATR & Vol
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=DEFAULT_ATR_LENGTH)
            atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else (curr_c * 0.01)

            # Volume Confirmation
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            curr_vol = df['Volume'].iloc[-1]
            vol_spike = (curr_vol > avg_vol * 1.5)

            if vol_spike:
                signal += " (Vol Spike)"

            # Targets/Stops
            stop_loss = curr_l - atr if "BULL" in signal else curr_h + atr
            target = curr_c + (3 * atr) if "BULL" in signal else curr_c - (3 * atr)

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            pct_change_1d = 0.0
            if len(df) >= 2:
                prev_c = float(df['Close'].iloc[-2])
                pct_change_1d = ((curr_c - prev_c) / prev_c) * 100

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": round(curr_c, 2),
                "signal": signal,
                "verdict": signal,
                "pct_change_1d": round(pct_change_1d, 2),
                "stop_loss": round(stop_loss, 2),
                "target": round(target, 2),
                "atr": round(atr, 2),
                "breakout_level": round(sweep_level, 2),
                "score": abs(displacement_pct) * 100,
                "breakout_date": _calculate_trend_breakout_date(df)
            }

        except Exception as e:
            return None

    results = runner.run(strategy)
    # Sort by Displacement/Score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results
