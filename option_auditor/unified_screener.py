import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time

from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.fourier import FourierStrategy
from option_auditor.common.constants import TICKER_NAMES, SECTOR_COMPONENTS

logger = logging.getLogger(__name__)

def screen_universal_dashboard(ticker_list: list = None, time_frame: str = "1d") -> list:
    """
    Runs ALL strategies on the provided ticker list using a single data fetch.
    Returns a unified "Master Signal" matrix.
    """
    if ticker_list is None:
        # Default to a mix if not provided
        ticker_list = ["SPY", "QQQ", "IWM", "AAPL", "NVDA", "MSFT", "TSLA", "AMD", "AMZN", "GOOGL"]
        if "WATCH" in SECTOR_COMPONENTS:
             ticker_list = list(set(ticker_list + SECTOR_COMPONENTS["WATCH"]))

    # 1. Download Data ONCE
    # Use 2 years to satisfy ISA (200 SMA) and Fourier
    period = "2y"
    yf_interval = "1d"

    # Adjust for timeframe if needed (though universal dashboard implies daily macro view usually)
    if time_frame != "1d":
        # Logic for intraday?
        # For now, let's assume this is a Daily Dashboard tool as described in "Morning Meeting".
        pass

    try:
        data = yf.download(ticker_list, period=period, interval=yf_interval, group_by='ticker', progress=False, auto_adjust=True, threads=True)
    except Exception as e:
        logger.error(f"Universal download failed: {e}")
        return []

    results = []

    # Initialize Strategies
    turtle_strat = TurtleStrategy()
    isa_strat = IsaStrategy()
    fourier_strat = FourierStrategy()

    def process_ticker(ticker):
        try:
            # Prepare DF
            df = pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                    df = data[ticker].copy()
            else:
                df = data.copy()

            df = df.dropna(how='all')
            if len(df) < 50: return None

            # Run Strategies
            turtle_res = turtle_strat.analyze(df)
            isa_res = isa_strat.analyze(df)
            fourier_res = fourier_strat.analyze(df)

            # Collate Verdict (Confluence)
            confluence_score = 0
            buy_signals = 0
            sell_signals = 0

            # Weighted Scoring?
            # Turtle Buy + ISA Buy = Strong Trend
            # Fourier Buy = Cycle Low

            # Count positive signals (BUY or strong HOLD/WATCH)
            if turtle_res['signal'] in ["BUY", "WATCH"]: buy_signals += 1
            if isa_res['signal'] in ["BUY", "WATCH", "HOLD"]: buy_signals += 1
            if fourier_res['signal'] == "BUY": buy_signals += 1

            if turtle_res['signal'] == "SELL": sell_signals += 1
            # ISA doesn't short usually, but if AVOID/EXIT?
            if isa_res['signal'] == "EXIT": sell_signals += 0.5
            if fourier_res['signal'] == "SELL": sell_signals += 1

            master_verdict = "WAIT"
            master_color = "gray"

            if buy_signals == 3:
                master_verdict = "🚀 STRONG BUY (3/3)"
                master_color = "green"
            elif buy_signals == 2:
                master_verdict = "✅ BUY (2/3 Confluence)"
                master_color = "green"
            elif buy_signals == 1:
                # Which one?
                if fourier_res['signal'] == "BUY":
                    master_verdict = "🌊 DIP BUY (Cycle Only)"
                    master_color = "blue"
                else:
                    master_verdict = "👀 WATCH (Trend Start)"
                    master_color = "yellow"

            if sell_signals >= 2:
                master_verdict = "🛑 STRONG SELL / AVOID"
                master_color = "red"

            base_ticker = ticker.split('.')[0]
            company_name = TICKER_NAMES.get(ticker, TICKER_NAMES.get(base_ticker, ticker))

            return {
                "ticker": ticker,
                "company_name": company_name,
                "price": float(df['Close'].iloc[-1]),
                "master_verdict": master_verdict,
                "master_color": master_color,
                "confluence_score": f"{buy_signals}/3",
                "strategies": {
                    "turtle": turtle_res,
                    "isa": isa_res,
                    "fourier": fourier_res
                }
            }

        except Exception as e:
            # logger.error(f"Error processing universal {ticker}: {e}")
            return None

    # Threaded Execution
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(process_ticker, sym): sym for sym in ticker_list}
        for future in as_completed(future_to_symbol):
            try:
                res = future.result()
                if res: results.append(res)
            except: pass

    # Sort by Buy Confluence
    results.sort(key=lambda x: x['confluence_score'], reverse=True)
    return results
