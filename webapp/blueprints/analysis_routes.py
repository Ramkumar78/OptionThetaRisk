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
from option_auditor.common.screener_utils import fetch_batch_data_safe
from webapp.storage import get_storage_provider as _get_storage_provider
from webapp.utils import _allowed_filename, handle_api_error
from option_auditor.common.serialization import serialize_ohlc_data

analysis_bp = Blueprint('analysis', __name__)

def get_db():
    if 'storage_provider' not in g:
        g.storage_provider = _get_storage_provider(current_app)
    return g.storage_provider

@analysis_bp.route("/analyze/portfolio", methods=["POST"])
@handle_api_error
def analyze_portfolio_route():
    data = request.json
    positions = data.get("positions", [])

    if not positions:
        return jsonify({"error": "No positions provided"}), 400

    report = portfolio_risk.analyze_portfolio_risk(positions)
    return jsonify(report)

@analysis_bp.route("/analyze/portfolio/greeks", methods=["POST"])
@handle_api_error
def analyze_portfolio_greeks_route():
    data = request.json
    positions = data.get("positions", [])

    if not positions:
        return jsonify({"error": "No positions provided"}), 400

    report = portfolio_risk.analyze_portfolio_greeks(positions)
    return jsonify(report)

@analysis_bp.route("/analyze/scenario", methods=["POST"])
@handle_api_error
def analyze_scenario_route():
    data = request.json
    positions = data.get("positions", [])
    scenario = data.get("scenario", {})

    if not positions:
        return jsonify({"error": "No positions provided"}), 400

    report = portfolio_risk.analyze_scenario(positions, scenario)
    return jsonify(report)

@analysis_bp.route("/analyze/correlation", methods=["POST"])
@handle_api_error
def analyze_correlation_route():
    data = request.json
    tickers = data.get("tickers", [])

    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(',')]

    period = data.get("period", "1y")

    result = calculate_correlation_matrix(tickers, period=period)

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/backtest", methods=["POST"])
@handle_api_error
def analyze_backtest_route():
    data = request.json
    ticker = data.get("ticker")
    strategy = data.get("strategy", "master")
    try:
        initial_capital = float(data.get("initial_capital", 10000.0))
    except ValueError:
        return jsonify({"error": "Initial Capital must be a number"}), 400

    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    backtester = UnifiedBacktester(ticker, strategy_type=strategy, initial_capital=initial_capital)
    result = backtester.run()

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/monte-carlo", methods=["POST"])
@handle_api_error
def analyze_monte_carlo_route():
    data = request.json
    ticker = data.get("ticker")
    strategy = data.get("strategy", "turtle")
    try:
        simulations = int(data.get("simulations", 10000))
    except ValueError:
        return jsonify({"error": "Simulations must be an integer"}), 400

    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    backtester = UnifiedBacktester(ticker, strategy_type=strategy)
    # We can call run_monte_carlo directly, it will run the backtest if needed.
    result = backtester.run_monte_carlo(simulations=simulations)

    if "error" in result:
            return jsonify(result), 400

    return jsonify(result)

@analysis_bp.route("/analyze/market-data", methods=["POST"])
@handle_api_error
def analyze_market_data_route():
    data = request.json
    ticker = data.get("ticker")
    period = data.get("period", "1y")

    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    # Fetch data
    df = fetch_batch_data_safe([ticker], period=period)

    if df.empty:
            return jsonify({"error": "No data found"}), 404

    chart_data = serialize_ohlc_data(df, ticker)
    return jsonify(chart_data)

@analysis_bp.route("/analyze", methods=["POST"])
@handle_api_error
def analyze():
    current_app.logger.info("Portfolio Audit Request received")
    file = request.files.get("csv")
    broker = request.form.get("broker", "auto")

    manual_data_json = request.form.get("manual_trades")
    manual_data = None
    if manual_data_json:
        try:
            manual_data = json.loads(manual_data_json)
            if manual_data and isinstance(manual_data, list):
                manual_data = [
                    row for row in manual_data
                    if row.get("date") and row.get("symbol") and row.get("action")
                ]
                if not manual_data:
                    manual_data = None
        except json.JSONDecodeError:
            pass

    def _to_float(name: str) -> Optional[float]:
        val = request.form.get(name, "").strip()
        if val:
            try:
                return float(val)
            except ValueError:
                return None
        return None

    account_size_start = _to_float("account_size_start")
    net_liquidity_now = _to_float("net_liquidity_now")
    buying_power_available_now = _to_float("buying_power_available_now")
    style = request.form.get("style", "income")
    fee_per_trade = _to_float("fee_per_trade")
    csv_fee_per_trade = _to_float("csv_fee_per_trade")

    if (not file or file.filename == "") and not manual_data:
        return jsonify({"error": "No input data provided"}), 400

    if file and file.filename != "" and not _allowed_filename(file.filename):
            return jsonify({"error": "Invalid file type"}), 400

    date_mode = request.form.get("date_mode", "all")
    start_date = request.form.get("start_date", "").strip() or None
    end_date = request.form.get("end_date", "").strip() or None

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
