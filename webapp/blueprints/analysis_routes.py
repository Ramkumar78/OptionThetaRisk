from flask import Blueprint, request, jsonify, session, current_app, send_file, g
import io
import os
import uuid
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from option_auditor import analyze_csv, portfolio_risk
from option_auditor.risk_intelligence import calculate_correlation_matrix
from option_auditor.unified_backtester import UnifiedBacktester
from option_auditor.backtesting_strategies import get_strategy
from option_auditor.common.screener_utils import fetch_batch_data_safe
from webapp.storage import get_storage_provider as _get_storage_provider
from webapp.utils import _allowed_filename, handle_api_error
from option_auditor.common.serialization import serialize_ohlc_data
from webapp.validation import validate_schema
from webapp.schemas import (
    PortfolioAnalysisRequest, ScenarioAnalysisRequest, CorrelationRequest,
    BacktestRequest, MonteCarloRequest, MarketDataRequest, AnalyzeRequest
)

analysis_bp = Blueprint('analysis', __name__)

def get_db():
    if 'storage_provider' not in g:
        g.storage_provider = _get_storage_provider(current_app)
    return g.storage_provider

@analysis_bp.route("/analyze/portfolio", methods=["POST"])
@handle_api_error
@validate_schema(PortfolioAnalysisRequest)
def analyze_portfolio_route():
    data: PortfolioAnalysisRequest = g.validated_data
    report = portfolio_risk.analyze_portfolio_risk(data.positions)
    return jsonify(report)

@analysis_bp.route("/analyze/portfolio/greeks", methods=["POST"])
@handle_api_error
@validate_schema(PortfolioAnalysisRequest)
def analyze_portfolio_greeks_route():
    data: PortfolioAnalysisRequest = g.validated_data
    report = portfolio_risk.analyze_portfolio_greeks(data.positions)
    return jsonify(report)

@analysis_bp.route("/analyze/scenario", methods=["POST"])
@handle_api_error
@validate_schema(ScenarioAnalysisRequest)
def analyze_scenario_route():
    data: ScenarioAnalysisRequest = g.validated_data
    report = portfolio_risk.analyze_scenario(data.positions, data.scenario)
    return jsonify(report)

@analysis_bp.route("/analyze/correlation", methods=["POST"])
@handle_api_error
@validate_schema(CorrelationRequest)
def analyze_correlation_route():
    data: CorrelationRequest = g.validated_data
    # tickers is already a list due to the validator
    result = calculate_correlation_matrix(data.tickers, period=data.period)

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/backtest", methods=["POST"])
@handle_api_error
@validate_schema(BacktestRequest)
def analyze_backtest_route():
    data: BacktestRequest = g.validated_data
    backtester = UnifiedBacktester(data.ticker, strategy_type=data.strategy, initial_capital=data.initial_capital)
    result = backtester.run()

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/monte-carlo", methods=["POST"])
@handle_api_error
@validate_schema(MonteCarloRequest)
def analyze_monte_carlo_route():
    data: MonteCarloRequest = g.validated_data
    backtester = UnifiedBacktester(data.ticker, strategy_type=data.strategy)
    # We can call run_monte_carlo directly, it will run the backtest if needed.
    result = backtester.run_monte_carlo(simulations=data.simulations)

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/market-data", methods=["POST"])
@handle_api_error
@validate_schema(MarketDataRequest)
def analyze_market_data_route():
    data: MarketDataRequest = g.validated_data
    # Fetch data
    df = fetch_batch_data_safe([data.ticker], period=data.period)

    if df.empty:
            return jsonify({"error": "No data found"}), 404

    chart_data = serialize_ohlc_data(df, data.ticker)
    return jsonify(chart_data)

@analysis_bp.route("/analyze/strategies", methods=["GET"])
@handle_api_error
def list_strategies_route():
    strategy_keys = [
        'master', 'turtle', 'isa', 'market', 'ema', 'darvas',
        'mms', 'bull_put', 'hybrid', 'fortress', 'quantum',
        'alpha101', 'liquidity_grab', 'rsi_divergence'
    ]

    strategies_info = []
    for key in strategy_keys:
        try:
            strategy_instance = get_strategy(key)
            explanation = strategy_instance.get_retail_explanation()
            strategies_info.append({
                "value": key,
                "explanation": explanation
            })
        except Exception as e:
            current_app.logger.warning(f"Could not load explanation for strategy {key}: {e}")
            strategies_info.append({
                "value": key,
                "explanation": "No explanation available."
            })

    return jsonify(strategies_info)

@analysis_bp.route("/analyze", methods=["POST"])
@handle_api_error
@validate_schema(AnalyzeRequest, source='form')
def analyze():
    current_app.logger.info("Portfolio Audit Request received")

    data: AnalyzeRequest = g.validated_data

    file = request.files.get("csv")
    broker = data.broker
    manual_data = data.manual_trades

    account_size_start = data.account_size_start
    net_liquidity_now = data.net_liquidity_now
    buying_power_available_now = data.buying_power_available_now
    style = data.style
    fee_per_trade = data.fee_per_trade
    csv_fee_per_trade = data.csv_fee_per_trade

    if (not file or file.filename == "") and not manual_data:
        return jsonify({"error": "No input data provided"}), 400

    if file and file.filename != "" and not _allowed_filename(file.filename):
            return jsonify({"error": "Invalid file type"}), 400

    date_mode = data.date_mode
    start_date = data.start_date
    end_date = data.end_date

    now = datetime.now()
    if date_mode in {"7d", "14d", "1m", "6m", "1y", "2y", "ytd"}:
        if date_mode == "7d": s_dt = now - timedelta(days=7)
        elif date_mode == "14d": s_dt = now - timedelta(days=14)
        elif date_mode == "1m": s_dt = now - timedelta(days=30)
        elif date_mode == "6m": s_dt = now - timedelta(days=182)
        elif date_mode == "1y": s_dt = now - timedelta(days=365)
        elif date_mode == "2y": s_dt = now - timedelta(days=730)
        else: s_dt = datetime(now.year, 1, 1)
        start_date = s_dt.date().isoformat()
        end_date = now.date().isoformat()

    token = uuid.uuid4().hex

    csv_path = None
    if file and file.filename != "":
        csv_path = io.StringIO(file.read().decode('utf-8'))

    final_global_fees = fee_per_trade if manual_data else csv_fee_per_trade

    res = analyze_csv(
        csv_path=csv_path,
        broker=broker,
        account_size_start=account_size_start,
        net_liquidity_now=net_liquidity_now,
        buying_power_available_now=buying_power_available_now,
        report_format="all",
        start_date=start_date,
        end_date=end_date,
        manual_data=manual_data,
        global_fees=final_global_fees,
        style=style
    )

    storage = get_db()

    if res.get("excel_report"):
        storage.save_report(token, "report.xlsx", res["excel_report"].getvalue())

    username = session.get('username')
    if username and "error" not in res:
        to_save = res.copy()
        if "excel_report" in to_save:
            del to_save["excel_report"]

        to_save["saved_at"] = datetime.now().isoformat()
        to_save["token"] = token
        to_save["style"] = style

        storage.save_portfolio(username, json.dumps(to_save).encode('utf-8'))

    if "excel_report" in res:
        del res["excel_report"]

    res["token"] = token
    current_app.logger.info("Portfolio Audit completed successfully.")
    return jsonify(res)

@analysis_bp.route("/download/<token>/<filename>")
def download(token: str, filename: str):
    storage = get_db()
    data = storage.get_report(token, filename)

    if not data:
            return "File not found", 404

    return send_file(
        io.BytesIO(data),
        as_attachment=True,
        download_name=filename
    )
