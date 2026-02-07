from flask import Blueprint, request, jsonify, current_app, g
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

from option_auditor import screener
from option_auditor.strategies.master import screen_master_convergence
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
from webapp.validation import validate_schema
from webapp.schemas import (
    ScreenerBaseRequest, ScreenerRunRequest, IsaCheckRequest,
    BacktestRunRequest, FourierScreenRequest, CheckStockRequest, IsaScreenRequest
)

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
@validate_schema(BacktestRunRequest, source='args')
def run_backtest():
    data: BacktestRunRequest = g.validated_data
    current_app.logger.info(f"Starting backtest: {data.strategy} on {data.ticker}")

    backtester = UnifiedBacktester(data.ticker, strategy_type=data.strategy)
    result = backtester.run()
    current_app.logger.info(f"Backtest completed for {data.ticker}")
    return jsonify(result)

@screener_bp.route("/screen", methods=["POST"])
@handle_screener_errors
@validate_schema(ScreenerRunRequest, source='form')
def screen():
    data: ScreenerRunRequest = g.validated_data
    current_app.logger.info(f"Screen request: region={data.region}, time={data.time_frame}")

    cache_key = ("market", data.iv_rank, data.rsi_threshold, data.time_frame, data.region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached screen result")
        return jsonify(cached)

    results = screener.screen_market(data.iv_rank, data.rsi_threshold, data.time_frame, region=data.region)
    sector_results = screener.screen_sectors(data.iv_rank, data.rsi_threshold, data.time_frame)
    data_resp = {
        "results": results,
        "sector_results": sector_results,
        "params": {"iv_rank": data.iv_rank, "rsi": data.rsi_threshold, "time_frame": data.time_frame, "region": data.region}
    }
    cache_screener_result(cache_key, data_resp)

    # Count results
    count = 0
    if isinstance(results, dict):
            count = sum(len(v) for v in results.values())
    else:
            count = len(results)

    current_app.logger.info(f"Screen completed. Results: {count}")
    if count == 0:
        current_app.logger.warning("Screen returned 0 results.")

    return jsonify(data_resp)

@screener_bp.route('/screen/turtle', methods=['GET'])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_turtle():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Turtle Screen request: region={data.region}")

    results = screener.screen_turtle_setups(region=data.region, time_frame=data.time_frame)
    current_app.logger.info(f"Turtle Screen completed. Results: {len(results)}")
    return jsonify(results)

@screener_bp.route("/screen/isa/check", methods=["GET"])
@handle_screener_errors
@validate_schema(IsaCheckRequest, source='args')
def check_isa_stock():
    data: IsaCheckRequest = g.validated_data
    current_app.logger.info(f"ISA Check request for {data.ticker}")

    # Position Sizing Param (Default £76k)
    account_size = data.account_size if data.account_size is not None else DEFAULT_ACCOUNT_SIZE

    ticker = screener.resolve_ticker(data.ticker)
    if not ticker:
        ticker = data.ticker.upper()

    results = screener.screen_trend_followers_isa(ticker_list=[ticker], account_size=account_size)

    if not results:
        current_app.logger.warning(f"ISA Check: No data found for {ticker}")
        return jsonify({"error": f"No data found for {ticker} or insufficient history."}), 404

    result = results[0]

    if data.entry_price and result.get('price'):
        curr = result['price']
        result['pnl_value'] = curr - data.entry_price
        result['pnl_pct'] = ((curr - data.entry_price) / data.entry_price) * 100
        result['user_entry_price'] = data.entry_price

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
@validate_schema(ScreenerBaseRequest, source='args')
def screen_alpha101():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Alpha 101 Screen request: region={data.region}, time_frame={data.time_frame}")

    cache_key = ("alpha101", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use the new function
    results = screener.screen_alpha_101(region=data.region, time_frame=data.time_frame)

    current_app.logger.info(f"Alpha 101 Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/mystrategy", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_my_strategy_route():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"MyStrategy Screen request: region={data.region}")

    cache_key = ("mystrategy", data.region)
    # Optional: Use caching if you implement it broadly
    cached = get_cached_screener_result(cache_key)
    if cached: return jsonify(cached)

    results = screener.screen_my_strategy(region=data.region)

    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/fortress", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_fortress():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Fortress Screen request: time_frame={data.time_frame}")
    cache_key = ("api_screen_fortress_us", data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached: return jsonify(cached)

    results = screener.screen_dynamic_volatility_fortress(time_frame=data.time_frame)

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
@validate_schema(IsaScreenRequest, source='args')
def screen_isa():
    data: IsaScreenRequest = g.validated_data
    current_app.logger.info(f"ISA Screen request: region={data.region}, time_frame={data.time_frame}")

    # Position Sizing Param (Default £76k)
    account_size = data.account_size if data.account_size is not None else DEFAULT_ACCOUNT_SIZE

    cache_key = ("isa", data.region, data.time_frame, account_size)
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached ISA screen result")
        return jsonify({"results": cached})

    # For ISA, if region is 'us', we prefer the broader S&P 500 list
    if data.region == 'us':
        tickers = resolve_region_tickers('sp500')
    else:
        tickers = resolve_region_tickers(data.region)

    # Correct Cache Name logic to use Shared Cache for US/SP500
    cache_name = f"market_scan_{data.region}"
    if data.region in ['us', 'united_states', 'sp500']:
        cache_name = "market_scan_v1"
    elif data.region == 'uk':
        cache_name = "market_scan_uk"
    elif data.region == 'india':
        cache_name = "market_scan_india"
    elif data.region == 'uk_euro':
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
@validate_schema(ScreenerBaseRequest, source='args')
def screen_bull_put():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Bull Put Screen request: region={data.region}, time_frame={data.time_frame}")

    cache_key = ("bull_put", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=True)

    results = screener.screen_bull_put_spreads(ticker_list=ticker_list, time_frame=data.time_frame)
    current_app.logger.info(f"Bull Put Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/vertical_put", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_vertical_put():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Vertical Put Screen request: region={data.region}")

    # Cache key
    cache_key = ("vertical_put_v2", data.region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Call the new logic
    results = screener.screen_vertical_put_spreads(region=data.region)

    current_app.logger.info(f"Vertical Put Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/darvas", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_darvas():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Darvas Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("darvas", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=True)

    results = screener.screen_darvas_box(ticker_list=ticker_list, time_frame=data.time_frame)
    current_app.logger.info(f"Darvas Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/ema", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_ema():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"EMA Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("ema", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=True)

    results = screener.screen_5_13_setups(ticker_list=ticker_list, time_frame=data.time_frame)
    current_app.logger.info(f"EMA Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/mms", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_mms():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"MMS Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("mms", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use only_watch=True for SP500 to avoid heavy load on intraday screens
    ticker_list = resolve_region_tickers(data.region, check_trend=False, only_watch=True)

    results = screener.screen_mms_ote_setups(ticker_list=ticker_list, time_frame=data.time_frame)
    current_app.logger.info(f"MMS Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/liquidity_grabs", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_liquidity_grabs():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Liquidity Grab Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("liquidity_grabs", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Use only_watch=True for SP500 to avoid heavy load on intraday screens
    ticker_list = resolve_region_tickers(data.region, check_trend=False, only_watch=True)

    results = screener.screen_liquidity_grabs(ticker_list=ticker_list, time_frame=data.time_frame, region=data.region)
    current_app.logger.info(f"Liquidity Grab Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/squeeze", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_squeeze():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Squeeze Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("squeeze", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_bollinger_squeeze(ticker_list=ticker_list, time_frame=data.time_frame, region=data.region)
    current_app.logger.info(f"Squeeze Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/hybrid", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_hybrid():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Hybrid Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("hybrid", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_hybrid_strategy(ticker_list=ticker_list, time_frame=data.time_frame, region=data.region)
    current_app.logger.info(f"Hybrid Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route('/screen/master', methods=['GET'])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_master():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Master Fortress Screen request: region={data.region}, time_frame={data.time_frame}")

    # Check Cache first (populated by Headless Scanner)
    cache_key = ("master", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        current_app.logger.info("Serving cached Master Screen result")
        return jsonify(cached)

    # The adapter handles the list logic internally based on region
    results = screen_master_convergence(region=data.region, time_frame=data.time_frame)

    # Cache result
    cache_screener_result(cache_key, results)

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
@validate_schema(FourierScreenRequest, source='args')
def screen_fourier():
    data: FourierScreenRequest = g.validated_data
    if data.ticker:
        current_app.logger.info(f"Fourier Single request: {data.ticker}")
        ticker = screener.resolve_ticker(data.ticker)
        if not ticker:
            ticker = data.ticker.upper()

        results = screener.screen_fourier_cycles(ticker_list=[ticker], time_frame="1d")
        if not results:
                return jsonify({"error": f"No cycle data found for {ticker}"}), 404
        return jsonify(results[0])

    current_app.logger.info(f"Fourier Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("fourier", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_fourier_cycles(ticker_list=ticker_list, time_frame=data.time_frame)
    current_app.logger.info(f"Fourier Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/rsi_divergence", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_rsi_divergence():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"RSI Divergence Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("rsi_divergence", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_rsi_divergence(ticker_list=ticker_list, time_frame=data.time_frame, region=data.region)
    current_app.logger.info(f"RSI Divergence Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/medallion_isa", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_medallion_isa():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Medallion ISA Screen request: region={data.region}, tf={data.time_frame}")

    cache_key = ("medallion_isa", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    # Resolve tickers
    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_medallion_isa(ticker_list=ticker_list, time_frame=data.time_frame, region=data.region)
    current_app.logger.info(f"Medallion ISA Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/api/screener/quality200", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_quality200():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Quality 200W Screen request: region={data.region}, time_frame={data.time_frame}")

    cache_key = ("quality_200w", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    results = screener.screen_quality_200w(region=data.region, time_frame=data.time_frame)

    current_app.logger.info(f"Quality 200W Screen completed. Results: {len(results)}")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/universal", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_universal():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Universal Screen request: region={data.region}")

    cache_key = ("universal", data.region)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    ticker_list = resolve_region_tickers(data.region, check_trend=False)

    results = screener.screen_universal_dashboard(ticker_list=ticker_list)
    current_app.logger.info(f"Universal Screen completed.")
    cache_screener_result(cache_key, results)
    return jsonify(results)

@screener_bp.route("/screen/quantum", methods=["GET"])
@handle_screener_errors
@validate_schema(ScreenerBaseRequest, source='args')
def screen_quantum():
    data: ScreenerBaseRequest = g.validated_data
    current_app.logger.info(f"Quantum Screen request: region={data.region}, time_frame={data.time_frame}")
    cache_key = ("quantum", data.region, data.time_frame)
    cached = get_cached_screener_result(cache_key)
    if cached:
        return jsonify(cached)

    results = screener.screen_quantum_setups(region=data.region, time_frame=data.time_frame)

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
@validate_schema(CheckStockRequest, source='args')
def check_unified_stock():
    data: CheckStockRequest = g.validated_data
    # Position Sizing Param (Default £76k)
    account_size = data.account_size if data.account_size is not None else DEFAULT_ACCOUNT_SIZE

    current_app.logger.info(f"Check Stock: {data.ticker}, Strategy: {data.strategy}")

    ticker = resolve_ticker(data.ticker)
    if not ticker:
        ticker = data.ticker.upper()

    entry_price = data.entry_price

    if entry_price is None and data.entry_date:
            try:
                dt = datetime.strptime(data.entry_date, "%Y-%m-%d")
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
        result = handle_check_stock(ticker, data.strategy, data.time_frame, account_size, entry_price)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not result:
        current_app.logger.info(f"No results for {ticker} in strategy {data.strategy}")
        return jsonify({"error": f"No data returned for {ticker} with strategy {data.strategy}."}), 404

    return jsonify(result)
