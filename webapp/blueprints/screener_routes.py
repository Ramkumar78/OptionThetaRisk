from flask import Blueprint, request, jsonify, current_app
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

from option_auditor import screener
from option_auditor.master_screener import screen_master_convergence
from option_auditor.unified_backtester import UnifiedBacktester
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.common.resilience import data_api_breaker
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.screener_utils import resolve_region_tickers, resolve_ticker
from option_auditor.uk_stock_data import get_uk_tickers
from option_auditor.us_stock_data import get_united_states_stocks
from option_auditor.common.constants import SECTOR_COMPONENTS, DEFAULT_ACCOUNT_SIZE

from webapp.cache import screener_cache, get_cached_screener_result, cache_screener_result
from webapp.utils import handle_screener_errors
from webapp.services.check_service import handle_check_stock

screener_bp = Blueprint('screener', __name__)

@screener_bp.route("/api/screener/status")
def get_breaker_status():
    """
    Returns the real-time status of the Circuit Breaker.
    Used by the frontend to display 'Stale Data' warnings.
    """
    return jsonify({
        "api_health": data_api_breaker.current_state, # 'closed', 'open', 'half-open'
        "is_fallback": data_api_breaker.current_state == 'open'
    })

@screener_bp.route('/backtest/run', methods=['GET'])
@handle_screener_errors
def run_backtest():
    ticker = request.args.get('ticker')
    strategy = request.args.get('strategy', 'master') # master, turtle, isa

    current_app.logger.info(f"Starting backtest: {strategy} on {ticker}")

    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    backtester = UnifiedBacktester(ticker, strategy_type=strategy)
    result = backtester.run()
    current_app.logger.info(f"Backtest completed for {ticker}")
    return jsonify(result)

@screener_bp.route("/screen", methods=["POST"])
@handle_screener_errors
def screen():
    iv_rank = 30.0
    try:
        iv_rank = float(request.form.get("iv_rank", 30))
    except ValueError:
        pass

    rsi_threshold = 50.0
    try:
        rsi_threshold = float(request.form.get("rsi_threshold", 50))
    except ValueError:
        pass

    time_frame = request.form.get("time_frame", "1d")
    region = request.form.get("region", "us")

    current_app.logger.info(f"Screen request: region={region}, time={time_frame}")

    cache_key = ("market", iv_rank, rsi_threshold, time_frame, region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached screen result")
        return jsonify(cached)

    results = screener.screen_market(iv_rank, rsi_threshold, time_frame, region=region)
    sector_results = screener.screen_sectors(iv_rank, rsi_threshold, time_frame)
    data = {
        "results": results,
        "sector_results": sector_results,
        "params": {"iv_rank": iv_rank, "rsi": rsi_threshold, "time_frame": time_frame, "region": region}
    }
    cache_screener_result(cache_key, data)

    # Count results
    count = 0
    if isinstance(results, dict):
            count = sum(len(v) for v in results.values())
    else:
            count = len(results)

    current_app.logger.info(f"Screen completed. Results: {count}")
    if count == 0:
        current_app.logger.warning("Screen returned 0 results.")

    return jsonify(data)

@screener_bp.route('/screen/turtle', methods=['GET'])
@handle_screener_errors
def screen_turtle():
    region = request.args.get('region', 'us')
    time_frame = request.args.get('time_frame', '1d')
    current_app.logger.info(f"Turtle Screen request: region={region}")

    results = screener.screen_turtle_setups(region=region, time_frame=time_frame)
    current_app.logger.info(f"Turtle Screen completed. Results: {len(results)}")
    return jsonify(results)

@screener_bp.route("/screen/isa/check", methods=["GET"])
@handle_screener_errors
def check_isa_stock():
    query = request.args.get("ticker", "").strip()
    if not query:
        return jsonify({"error": "No ticker provided"}), 400

    current_app.logger.info(f"ISA Check request for {query}")

    # Position Sizing Param (Default £76k)
    account_size = DEFAULT_ACCOUNT_SIZE
    acc_size_str = request.args.get("account_size", "").strip()
    if acc_size_str:
        try:
            account_size = float(acc_size_str)
        except ValueError:
            pass

    entry_price = None
    entry_str = request.args.get("entry_price", "").strip()
    if entry_str:
        try:
            entry_price = float(entry_str)
        except ValueError:
            pass  # Ignore invalid float format

    ticker = screener.resolve_ticker(query)
    if not ticker:
        ticker = query.upper()

    results = screener.screen_trend_followers_isa(ticker_list=[ticker], account_size=account_size)

    if not results:
        current_app.logger.warning(f"ISA Check: No data found for {ticker}")
        return jsonify({"error": f"No data found for {ticker} or insufficient history."}), 404

    result = results[0]

    if entry_price and result.get('price'):
        curr = result['price']
        result['pnl_value'] = curr - entry_price
        result['pnl_pct'] = ((curr - entry_price) / entry_price) * 100
        result['user_entry_price'] = entry_price

        signal = result.get('signal', 'WAIT')
        stop_exit = result.get('trailing_exit_20d', 0)

        if "ENTER" in signal or "WATCH" in signal:
                result['signal'] = "✅ HOLD (Trend Active)"

        if curr <= stop_exit:
            result['signal'] = "🛑 EXIT (Stop Hit)"

        if "SELL" in signal or "AVOID" in signal:
                result['signal'] = "🛑 EXIT (Downtrend)"

    current_app.logger.info(f"ISA Check result for {ticker}: {result.get('signal')}")
    return jsonify(result)

@screener_bp.route("/screen/alpha101", methods=["GET"])
@handle_screener_errors
def screen_alpha101():
    region = request.args.get("region", "us")
    time_frame = request.args.get("time_frame", "1d")
    current_app.logger.info(f"Alpha 101 Screen request: region={region}, time_frame={time_frame}")

    cache_key = ("alpha101", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use the new function
    results = screener.screen_alpha_101(region=region, time_frame=time_frame)

    current_app.logger.info(f"Alpha 101 Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/mystrategy", methods=["GET"])
@handle_screener_errors
def screen_my_strategy_route():
    region = request.args.get("region", "us")
    current_app.logger.info(f"MyStrategy Screen request: region={region}")

    cache_key = ("mystrategy", region)
    # Optional: Use caching if you implement it broadly
    cached = get_cached_screener_result(cache_key)
    if cached: return jsonify(cached)

    results = screener.screen_my_strategy(region=region)

    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/fortress", methods=["GET"])
@handle_screener_errors
def screen_fortress():
    time_frame = request.args.get("time_frame", "1d")
    current_app.logger.info(f"Fortress Screen request: time_frame={time_frame}")
    cache_key = ("api_screen_fortress_us", time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached: return jsonify(cached)

    results = screener.screen_dynamic_volatility_fortress(time_frame=time_frame)

    current_app.logger.info(f"Fortress Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/options_only", methods=["GET"])
@handle_screener_errors
def screen_options_only():
    current_app.logger.info("Thalaiva Options Only Screen Initiated")

    # Cache Key
    cache_key = ("options_only_scanner", "us")
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached Options Only results")
        return jsonify(cached)

    # Run with limit=75 to be safe
    results = screener.screen_options_only_strategy(limit=75)

    # Cache results
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route('/screen/isa', methods=['GET'])
@handle_screener_errors
def screen_isa():
    region = request.args.get('region', 'us')
    time_frame = request.args.get('time_frame', '1d')
    current_app.logger.info(f"ISA Screen request: region={region}, time_frame={time_frame}")

    # Position Sizing Param (Default £76k)
    account_size = DEFAULT_ACCOUNT_SIZE
    acc_size_str = request.args.get("account_size", "").strip()
    if acc_size_str:
        try:
            account_size = float(acc_size_str)
        except ValueError:
            pass

    cache_key = ("isa", region, time_frame, account_size)
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached ISA screen result")
        return jsonify({"results": cached})

    # For ISA, if region is 'us', we prefer the broader S&P 500 list
    if region == 'us':
        tickers = resolve_region_tickers('sp500')
    else:
        tickers = resolve_region_tickers(region)

    # Correct Cache Name logic to use Shared Cache for US/SP500
    cache_name = f"market_scan_{region}"
    if region in ['us', 'united_states', 'sp500']:
        cache_name = "market_scan_v1"
    elif region == 'uk':
        cache_name = "market_scan_uk"
    elif region == 'india':
        cache_name = "market_scan_india"
    elif region == 'uk_euro':
            cache_name = "market_scan_europe"

    results = []

    data = get_cached_market_data(tickers, period="2y", cache_name=cache_name)

    if data.empty:
        current_app.logger.warning("ISA Screen: Data empty")
        return jsonify([])

    # Robust Iteration Logic (Handles both MultiIndex and Flat DataFrames)
    iterator = []
    if isinstance(data.columns, pd.MultiIndex):
        # Standard Batch Result: Iterate over Level 0 (Tickers)
        iterator = [(ticker, data[ticker]) for ticker in data.columns.unique(level=0)]
    else:
        # Flat Result (Single Ticker or Flattened)
        # If we asked for 1 ticker, this is expected.
        # If we asked for 500, this is bad unless only 1 returned.
        if len(tickers) == 1:
                iterator = [(tickers[0], data)]
        elif not data.empty:
                # Attempt to use as is if ambiguous, or skip
                # Usually shouldn't happen with fetch_batch_data_safe unless strict single mode
                pass

    for ticker, df_raw in iterator:
        try:
            if ticker not in tickers: continue

            # Ensure df is clean
            df = df_raw.dropna(how='all')

            if df is not None and not df.empty:
                # Handle potential MultiIndex columns remaining (rare)
                if isinstance(df.columns, pd.MultiIndex):
                    df = df.droplevel(0, axis=1)

                strategy = IsaStrategy(ticker, df, account_size=account_size)
                res = strategy.analyze()
                if res and res['Signal'] != 'WAIT':
                    results.append(res)
        except Exception as e:
            # Log but continue - prevent one bad ticker from killing the loop
            # current_app.logger.warning(f"ISA Screen failed for {ticker}: {e}")
            continue

    current_app.logger.info(f"ISA Screen completed. Results: {len(results)}")

    # Cache the successful result
    cache_screener_result(cache_key, results)

    return jsonify({"results": results})

@screener_bp.route("/screen/bull_put", methods=["GET"])
@handle_screener_errors
def screen_bull_put():
    region = request.args.get("region", "us")
    time_frame = request.args.get("time_frame", "1d")
    current_app.logger.info(f"Bull Put Screen request: region={region}, time_frame={time_frame}")

    cache_key = ("bull_put", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=True)

    results = screener.screen_bull_put_spreads(ticker_list=ticker_list, time_frame=time_frame)
    current_app.logger.info(f"Bull Put Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/vertical_put", methods=["GET"])
@handle_screener_errors
def screen_vertical_put():
    region = request.args.get("region", "us")
    current_app.logger.info(f"Vertical Put Screen request: region={region}")

    # Cache key
    cache_key = ("vertical_put_v2", region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Call the new logic
    results = screener.screen_vertical_put_spreads(region=region)

    current_app.logger.info(f"Vertical Put Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/darvas", methods=["GET"])
@handle_screener_errors
def screen_darvas():
    time_frame = request.args.get("time_frame", "1d")
    region = request.args.get("region", "us")
    current_app.logger.info(f"Darvas Screen request: region={region}, tf={time_frame}")

    cache_key = ("darvas", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=True)

    results = screener.screen_darvas_box(ticker_list=ticker_list, time_frame=time_frame)
    current_app.logger.info(f"Darvas Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/ema", methods=["GET"])
@handle_screener_errors
def screen_ema():
    time_frame = request.args.get("time_frame", "1d")
    region = request.args.get("region", "us")
    current_app.logger.info(f"EMA Screen request: region={region}, tf={time_frame}")

    cache_key = ("ema", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=True)

    results = screener.screen_5_13_setups(ticker_list=ticker_list, time_frame=time_frame)
    current_app.logger.info(f"EMA Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/mms", methods=["GET"])
@handle_screener_errors
def screen_mms():
    time_frame = request.args.get("time_frame", "1h")
    region = request.args.get("region", "us")
    current_app.logger.info(f"MMS Screen request: region={region}, tf={time_frame}")

    cache_key = ("mms", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use only_watch=True for SP500 to avoid heavy load on intraday screens
    ticker_list = resolve_region_tickers(region, check_trend=False, only_watch=True)

    results = screener.screen_mms_ote_setups(ticker_list=ticker_list, time_frame=time_frame)
    current_app.logger.info(f"MMS Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/liquidity_grabs", methods=["GET"])
@handle_screener_errors
def screen_liquidity_grabs():
    time_frame = request.args.get("time_frame", "1h")
    region = request.args.get("region", "us")
    current_app.logger.info(f"Liquidity Grab Screen request: region={region}, tf={time_frame}")

    cache_key = ("liquidity_grabs", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use only_watch=True for SP500 to avoid heavy load on intraday screens
    ticker_list = resolve_region_tickers(region, check_trend=False, only_watch=True)

    results = screener.screen_liquidity_grabs(ticker_list=ticker_list, time_frame=time_frame, region=region)
    current_app.logger.info(f"Liquidity Grab Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/squeeze", methods=["GET"])
@handle_screener_errors
def screen_squeeze():
    time_frame = request.args.get("time_frame", "1d")
    region = request.args.get("region", "us")
    current_app.logger.info(f"Squeeze Screen request: region={region}, tf={time_frame}")

    cache_key = ("squeeze", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=False)

    results = screener.screen_bollinger_squeeze(ticker_list=ticker_list, time_frame=time_frame, region=region)
    current_app.logger.info(f"Squeeze Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/hybrid", methods=["GET"])
@handle_screener_errors
def screen_hybrid():
    time_frame = request.args.get("time_frame", "1d")
    region = request.args.get("region", "us")
    current_app.logger.info(f"Hybrid Screen request: region={region}, tf={time_frame}")

    cache_key = ("hybrid", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=False)

    results = screener.screen_hybrid_strategy(ticker_list=ticker_list, time_frame=time_frame, region=region)
    current_app.logger.info(f"Hybrid Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route('/screen/master', methods=['GET'])
@handle_screener_errors
def screen_master():
    region = request.args.get('region', 'us')
    time_frame = request.args.get('time_frame', '1d')
    current_app.logger.info(f"Master Fortress Screen request: region={region}, time_frame={time_frame}")

    # The adapter handles the list logic internally based on region
    results = screen_master_convergence(region=region, time_frame=time_frame)

    # Ensure it returns a list directly, or wrap in dict if frontend expects {results: [...]}
    # Based on your previous code, it seems to handle both, but let's be safe:
    count = len(results)
    current_app.logger.info(f"Fortress Screen completed. Results: {count}")

    # Frontend often expects { "results": [...] } or just [...]
    # Let's standardise on the list for this specific route if the frontend grid handles it
    return jsonify(results)

@screener_bp.route('/screen/quant', methods=['GET'])
def screen_quant():
    # Redirect Quant requests to the Fortress as well, since QuantMasterScreener (OpenBB) is broken
    # Using screen_master() directly, which is decorated, so it's handled.
    return screen_master()

@screener_bp.route("/screen/fourier", methods=["GET"])
@handle_screener_errors
def screen_fourier():
    query = request.args.get("ticker", "").strip()
    if query:
        current_app.logger.info(f"Fourier Single request: {query}")
        ticker = screener.resolve_ticker(query)
        if not ticker:
            ticker = query.upper()

        results = screener.screen_fourier_cycles(ticker_list=[ticker], time_frame="1d")
        if not results:
                return jsonify({"error": f"No cycle data found for {ticker}"}), 404
        return jsonify(results[0])

    time_frame = request.args.get("time_frame", "1d")
    region = request.args.get("region", "us")
    current_app.logger.info(f"Fourier Screen request: region={region}, tf={time_frame}")

    cache_key = ("fourier", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=False)

    results = screener.screen_fourier_cycles(ticker_list=ticker_list, time_frame=time_frame)
    current_app.logger.info(f"Fourier Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/rsi_divergence", methods=["GET"])
@handle_screener_errors
def screen_rsi_divergence():
    region = request.args.get("region", "us")
    time_frame = request.args.get("time_frame", "1d")
    current_app.logger.info(f"RSI Divergence Screen request: region={region}, tf={time_frame}")

    cache_key = ("rsi_divergence", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=False)

    results = screener.screen_rsi_divergence(ticker_list=ticker_list, time_frame=time_frame, region=region)
    current_app.logger.info(f"RSI Divergence Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/universal", methods=["GET"])
@handle_screener_errors
def screen_universal():
    region = request.args.get("region", "us")
    current_app.logger.info(f"Universal Screen request: region={region}")

    cache_key = ("universal", region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(region, check_trend=False)

    results = screener.screen_universal_dashboard(ticker_list=ticker_list)
    current_app.logger.info(f"Universal Screen completed.")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/quantum", methods=["GET"])
@handle_screener_errors
def screen_quantum():
    region = request.args.get("region", "us")
    time_frame = request.args.get("time_frame", "1d")
    current_app.logger.info(f"Quantum Screen request: region={region}, time_frame={time_frame}")
    cache_key = ("quantum", region, time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    results = screener.screen_quantum_setups(region=region, time_frame=time_frame)

    api_results = [
        {
            "ticker": r["ticker"],
            "price": r["price"],
            "hurst": round(r["hurst"], 2) if r["hurst"] else None,
            "entropy": round(r["entropy"], 2) if r["entropy"] else None,
            "verdict": r["signal"],
            "score": r["score"],
            "company_name": r.get("company_name"),
            "kalman_diff": round(r["kalman_diff"], 2) if r["kalman_diff"] else None,
            "phase": round(r["phase"], 2) if r.get("phase") else None,
            "verdict_color": r.get("verdict_color"),
            "atr_value": r.get("atr_value"),
            "volatility_pct": r.get("volatility_pct"),
            "pct_change_1d": r.get("pct_change_1d"),
            "breakout_date": r.get("breakout_date"),
            "kalman_signal": r.get("kalman_signal"),
            "human_verdict": r.get("human_verdict"),
            "rationale": r.get("rationale")
        } for r in results
    ]

    current_app.logger.info(f"Quantum Screen completed. Results: {len(api_results)}")
    cache_screener_result(cache_key, api_results)
    return jsonify(api_results)

@screener_bp.route("/screen/check", methods=["GET"])
@handle_screener_errors
def check_unified_stock():
    ticker_query = request.args.get("ticker", "").strip()
    strategy = request.args.get("strategy", "isa").lower()
    time_frame = request.args.get("time_frame", "1d")
    entry_price_str = request.args.get("entry_price", "").strip()
    entry_date_str = request.args.get("entry_date", "").strip()

    # Position Sizing Param (Default £76k)
    account_size = DEFAULT_ACCOUNT_SIZE
    acc_size_str = request.args.get("account_size", "").strip()
    if acc_size_str:
        try:
            account_size = float(acc_size_str)
        except ValueError:
            pass

    current_app.logger.info(f"Check Stock: {ticker_query}, Strategy: {strategy}")

    if not ticker_query:
        return jsonify({"error": "No ticker provided"}), 400

    ticker = resolve_ticker(ticker_query)
    if not ticker:
        ticker = ticker_query.upper()

    entry_price = None
    if entry_price_str:
        try:
            entry_price = float(entry_price_str)
        except ValueError:
            pass  # Ignore invalid float format

    if entry_price is None and entry_date_str:
            try:
                dt = datetime.strptime(entry_date_str, "%Y-%m-%d")
                hist = yf.download(ticker, start=dt, end=dt + timedelta(days=5), progress=False, auto_adjust=True)
                if not hist.empty:
                    try:
                        close_series = hist['Close']
                        val = None
                        if isinstance(close_series, pd.DataFrame):
                            val = close_series.iloc[0, 0]
                        else:
                            val = close_series.iloc[0]

                        if val is not None:
                            entry_price = float(val)
                    except Exception as inner:
                        current_app.logger.warning(f"Error accessing Close price: {inner}")
                        pass
            except Exception as e:
                current_app.logger.warning(f"Error fetching historical price for {ticker}: {e}")
                pass

    try:
        result = handle_check_stock(ticker, strategy, time_frame, account_size, entry_price)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not result:
        current_app.logger.info(f"No results for {ticker} in strategy {strategy}")
        return jsonify({"error": f"No data returned for {ticker} with strategy {strategy}."}), 404

    return jsonify(result)
