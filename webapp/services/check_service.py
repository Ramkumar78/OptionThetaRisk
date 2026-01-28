import logging
from option_auditor import screener

logger = logging.getLogger(__name__)

def handle_check_stock(ticker, strategy, time_frame, account_size, entry_price=None):
    """
    Handles the check_unified_stock logic: dispatches to strategy and formats result.
    """
    results = []

    # Dispatch Logic
    if strategy == "isa":
        results = screener.screen_trend_followers_isa(ticker_list=[ticker], check_mode=True, account_size=account_size)
    elif strategy == "turtle":
        results = screener.screen_turtle_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
    elif strategy == "darvas":
        results = screener.screen_darvas_box(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
    elif strategy == "ema" or strategy == "5/13":
        results = screener.screen_5_13_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
    elif strategy == "bull_put":
        results = screener.screen_bull_put_spreads(ticker_list=[ticker], check_mode=True)
    elif strategy == "hybrid":
        results = screener.screen_hybrid_strategy(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
    elif strategy == "mms":
        results = screener.screen_mms_ote_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
    elif strategy == "fourier":
        results = screener.screen_fourier_cycles(ticker_list=[ticker], time_frame=time_frame)
    elif strategy == "master":
        results = screener.screen_master_convergence(ticker_list=[ticker], check_mode=True)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    if not results:
        return None

    result = results[0]

    # Verdict Logic
    if entry_price and result.get('price'):
        curr = result['price']
        result['pnl_value'] = curr - entry_price
        result['pnl_pct'] = ((curr - entry_price) / entry_price) * 100
        result['user_entry_price'] = entry_price

        signal = str(result.get('signal', 'WAIT')).upper()
        verdict = str(result.get('verdict', '')).upper()

        if strategy == "isa":
            stop_exit = result.get('trailing_exit_20d', 0)
            if curr <= stop_exit:
                result['user_verdict'] = "🛑 EXIT (Stop Hit - Below 20d Low)"
            elif "SELL" in signal or "AVOID" in signal:
                result['user_verdict'] = "🛑 EXIT (Trend Reversed)"
            else:
                result['user_verdict'] = "✅ HOLD (Trend Valid)"

        elif strategy == "turtle":
            trailing_exit = result.get('trailing_exit_10d', 0)
            sl = result.get('stop_loss', 0)
            if trailing_exit > 0 and curr < trailing_exit:
                result['user_verdict'] = "🛑 EXIT (Below 10-Day Low)"
            elif sl > 0 and curr < sl:
                result['user_verdict'] = "🛑 EXIT (Stop Loss Hit)"
            else:
                result['user_verdict'] = "✅ HOLD (Trend Valid)"

        elif strategy == "ema":
            if "SELL" in signal or "DUMP" in signal:
                result['user_verdict'] = "🛑 EXIT (Bearish Cross)"
            else:
                result['user_verdict'] = "✅ HOLD (Momentum)"

        elif strategy == "fourier":
            if "HIGH" in signal or "SELL" in signal:
                result['user_verdict'] = "🛑 EXIT (Cycle Peak)"
            elif "LOW" in signal or "BUY" in signal:
                result['user_verdict'] = "✅ HOLD/ADD (Cycle Bottom)"
            else:
                result['user_verdict'] = "✅ HOLD (Mid-Cycle)"

        elif strategy == "master":
            score = result.get('confluence_score', 0)
            if score >= 2:
                result['user_verdict'] = f"✅ STAY LONG ({score}/3 Bullish)"
            else:
                isa = result.get('isa_trend', 'NEUTRAL')
                fourier = result.get('fourier', '')
                if isa == "BEARISH" and "TOP" in str(fourier).upper():
                    result['user_verdict'] = "🛑 URGENT EXIT (Trend & Cycle Bearish)"
                elif score == 1:
                    result['user_verdict'] = "⚠️ CAUTION (Only 1/3 Bullish)"
                else:
                    result['user_verdict'] = "🛑 EXIT (No Confluence)"

        if 'user_verdict' not in result:
            if "BUY" in signal or "GREEN" in signal or "BREAKOUT" in signal or "LONG" in signal or "BUY" in verdict:
                result['user_verdict'] = "✅ HOLD (Signal Active)"
            elif "SELL" in signal or "SHORT" in signal or "DUMP" in signal or "SELL" in verdict:
                result['user_verdict'] = "🛑 EXIT (Signal Bearish)"
            else:
                result['user_verdict'] = "👀 WATCH (Neutral)"

    return result
