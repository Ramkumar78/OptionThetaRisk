from __future__ import annotations

import io
import os
import uuid
import threading
import time
import json
from typing import Optional

from flask import Flask, request, redirect, url_for, flash, send_file, session, jsonify, send_from_directory

from option_auditor import analyze_csv, screener, journal_analyzer
from option_auditor.main_analyzer import refresh_dashboard_data
from datetime import datetime, timedelta
from webapp.storage import get_storage_provider
import resend
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
load_dotenv()

# Cleanup interval in seconds
CLEANUP_INTERVAL = 1200 # 20 minutes
# Max age of reports in seconds
MAX_REPORT_AGE = 1200 # 20 minutes

# Screener Cache
SCREENER_CACHE = {}
SCREENER_CACHE_TIMEOUT = 600  # 10 minutes

def get_cached_screener_result(key):
    if key in SCREENER_CACHE:
        timestamp, data = SCREENER_CACHE[key]
        if time.time() - timestamp < SCREENER_CACHE_TIMEOUT:
            return data
        else:
            del SCREENER_CACHE[key]
    return None

def cache_screener_result(key, data):
    SCREENER_CACHE[key] = (time.time(), data)

# Helper Function for Email
def _get_env_or_docker_default(key, default=None):
    """
    Get environment variable, or fall back to docker-compose.yml default if available.
    This helps in environments like Render that don't use docker-compose but have the file.
    """
    val = os.environ.get(key)
    if val:
        return val

    # Try to parse docker-compose.yml for defaults like ${VAR:-default}
    try:
        docker_compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docker-compose.yml')
        if os.path.exists(docker_compose_path):
            with open(docker_compose_path, 'r') as f:
                content = f.read()
                # Regex to find specific key pattern: key=${key:-value}
                # Handles lines like: - SMTP_USER=${SMTP_USER:-tradeauditor9@gmail.com}
                import re
                match = re.search(fr"{key}=\${{{key}:-(.*?)}}", content)
                if match:
                    return match.group(1)
    except Exception:
        pass

    return default

def send_email_notification(subject, body):
    api_key = _get_env_or_docker_default("RESEND_API_KEY")
    if not api_key:
        print("⚠️  Resend API Key missing. Skipping email.", flush=True)
        return

    resend.api_key = api_key

    # Intended recipients
    # Note: On free/testing tier, can only send to the account email (shriram2222@gmail.com)
    recipients = ["shriram2222@gmail.com"]

    print(f"📧 Sending email via Resend to {recipients}...", flush=True)

    try:
        params = {
            "from": "Trade Auditor <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "text": body,
        }

        email = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {email.get('id')}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send email: {e}", flush=True)

def cleanup_job(app):
    """Background thread to clean up old reports."""
    with app.app_context():
        storage = get_storage_provider(app)
        while True:
            try:
                storage.cleanup_old_reports(MAX_REPORT_AGE)
            except Exception:
                pass
            time.sleep(CLEANUP_INTERVAL)

def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__, instance_relative_config=True, static_folder="static")
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.config["TESTING"] = testing
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(16))
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))

    # Session config
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=90) # Longer session for guest persistence

    if not testing and (not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
        t = threading.Thread(target=cleanup_job, args=(app,), daemon=True)
        t.start()

    ALLOWED_EXTENSIONS = {".csv"}

    def _allowed_filename(filename: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        return ext in ALLOWED_EXTENSIONS

    @app.after_request
    def add_security_headers(response):
        # Adjusted CSP for React compatibility (removed some strict directives for now to ensure easier dev)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "object-src 'none';"
        )
        return response

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Upload too large. Max size is limited."}), 413

    @app.before_request
    def ensure_guest_session():
        # Ensure every visitor has a username (UUID) for storage keyed by username
        if 'username' not in session:
            session['username'] = f"guest_{uuid.uuid4().hex}"
            session.permanent = True

    @app.route("/feedback", methods=["POST"])
    def feedback():
        message = request.form.get("message", "").strip()
        name = request.form.get("name", "").strip() or None
        email = request.form.get("email", "").strip() or None
        username = session.get("username", "Anonymous")

        if message:
            storage = get_storage_provider(app)
            try:
                storage.save_feedback(username, message, name=name, email=email)

                # --- NEW CODE: Send Email ---
                email_body = f"User: {username}\nName: {name or 'N/A'}\nEmail: {email or 'N/A'}\n\nMessage:\n{message}"
                # Run in background to avoid blocking response
                threading.Thread(target=send_email_notification, args=(f"New Feedback from {username}", email_body)).start()
                # ---------------------------

                return jsonify({"success": True, "message": "Feedback submitted"})
            except Exception as e:
                print(f"Feedback error: {e}")
                return jsonify({"error": "Failed to submit feedback"}), 500
        else:
            return jsonify({"error": "Message cannot be empty"}), 400

    @app.route("/dashboard")
    def dashboard():
        username = session.get('username')
        if not username:
             return jsonify({"error": "No session"}), 401

        storage = get_storage_provider(app)
        data_bytes = storage.get_portfolio(username)

        if not data_bytes:
            return jsonify({"error": "No portfolio found"})

        try:
            saved_data = json.loads(data_bytes)
            updated_data = refresh_dashboard_data(saved_data)
            return jsonify(updated_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/health")
    def health():
        return "OK", 200

    # API Routes for Screener
    @app.route("/screen", methods=["POST"])
    def screen():
        # Handle JSON input if present (preferred for nested creds), else Form
        json_data = request.get_json(silent=True) or {}

        iv_rank = 30.0
        try:
            val = json_data.get("iv_rank") or request.form.get("iv_rank")
            if val: iv_rank = float(val)
        except ValueError:
            pass

        rsi_threshold = 50.0
        try:
            val = json_data.get("rsi_threshold") or request.form.get("rsi_threshold")
            if val: rsi_threshold = float(val)
        except ValueError:
            pass

        time_frame = json_data.get("time_frame") or request.form.get("time_frame") or "1d"
        tasty_creds = json_data.get("tasty_creds") # Expecting dict

        # Cache key includes credentials status to avoid serving public data to auth user and vice versa
        has_creds = 1 if tasty_creds else 0
        cache_key = ("market", iv_rank, rsi_threshold, time_frame, has_creds)

        # Only cache if NO creds (personal data shouldn't be shared cache, though for now we assume single user/guest)
        # Actually, if creds are invalid, we fall back to YF.
        # Let's skip cache read if creds are provided to ensure fresh live data.
        if not has_creds:
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

        try:
            results = screener.screen_market(iv_rank, rsi_threshold, time_frame, tasty_creds=tasty_creds)
            sector_results = screener.screen_sectors(iv_rank, rsi_threshold, time_frame)
            data = {
                "results": results,
                "sector_results": sector_results,
                "params": {"iv_rank": iv_rank, "rsi": rsi_threshold, "time_frame": time_frame}
            }
            # Only cache if no creds
            if not has_creds:
                cache_screener_result(cache_key, data)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/turtle", methods=["GET"])
    def screen_turtle():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")

            cache_key = ("turtle", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_turtle_setups(ticker_list=ticker_list, time_frame=time_frame)
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/bull_put", methods=["GET"])
    def screen_bull_put():
        try:
            # Bull Put Spreads are mainly for liquid US stocks for now
            # region param is accepted but we might just use default liquid list if us
            region = request.args.get("region", "us")

            cache_key = ("bull_put", region)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            # Use default list in function for now unless specific requirement
            results = screener.screen_bull_put_spreads()
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/darvas", methods=["GET"])
    def screen_darvas():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")

            cache_key = ("darvas", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_darvas_box(ticker_list=ticker_list, time_frame=time_frame)
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/ema", methods=["GET"])
    def screen_ema():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")

            cache_key = ("ema", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_5_13_setups(ticker_list=ticker_list, time_frame=time_frame)
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/mms", methods=["GET"])
    def screen_mms():
        try:
            time_frame = request.args.get("time_frame", "1h")
            region = request.args.get("region", "us")

            cache_key = ("mms", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_mms_ote_setups(ticker_list=ticker_list, time_frame=time_frame)
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # API Routes for Journal
    @app.route("/journal", methods=["GET"])
    def journal_get_entries():
        username = session.get('username')
        storage = get_storage_provider(app)
        entries = storage.get_journal_entries(username)
        return jsonify(entries)

    @app.route("/journal/add", methods=["POST"])
    def journal_add_entry():
        username = session.get('username')
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400

        data['username'] = username
        data['created_at'] = time.time()

        storage = get_storage_provider(app)
        try:
            entry_id = storage.save_journal_entry(data)
            return jsonify({"success": True, "id": entry_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/journal/delete/<entry_id>", methods=["DELETE"])
    def journal_delete_entry(entry_id):
        username = session.get('username')
        storage = get_storage_provider(app)
        storage.delete_journal_entry(username, entry_id)
        return jsonify({"success": True})

    @app.route("/journal/analyze", methods=["POST"])
    def journal_analyze_batch():
        username = session.get('username')
        storage = get_storage_provider(app)
        entries = storage.get_journal_entries(username)
        result = journal_analyzer.analyze_journal(entries)
        return jsonify(result)

    @app.route("/journal/import", methods=["POST"])
    def journal_import_trades():
        username = session.get('username')
        data = request.json
        if not data or not isinstance(data, list):
            return jsonify({"error": "Invalid data format. Expected list of trades."}), 400

        storage = get_storage_provider(app)
        count = 0
        try:
            for trade in data:
                # Map analysis trade object to journal entry
                # trade is likely a dict from strategy_rows in main_analyzer

                # Extract entry date from segments if available
                entry_date = ""
                entry_time = ""
                if trade.get("segments") and len(trade.get("segments")) > 0:
                    first_seg = trade["segments"][0]
                    ts_str = first_seg.get("entry_ts", "")
                    if ts_str:
                         try:
                             dt = datetime.fromisoformat(ts_str)
                             entry_date = dt.date().isoformat()
                             entry_time = dt.time().isoformat()
                         except:
                             pass

                # Fallback to current date if missing (though analysis results usually have dates)
                if not entry_date:
                    entry_date = datetime.now().date().isoformat()

                journal_entry = {
                    "id": str(uuid.uuid4()),
                    "username": username,
                    "entry_date": entry_date,
                    "entry_time": entry_time,
                    "symbol": trade.get("symbol", ""),
                    "strategy": trade.get("strategy", ""),
                    "direction": "", # Not explicit in strategy object, user can edit
                    "entry_price": 0.0, # Not explicit aggregated
                    "exit_price": 0.0,
                    "qty": 1.0, # Strategy level aggregation
                    "pnl": float(trade.get("pnl", 0.0)),
                    "notes": f"Imported Analysis. Legs: {trade.get('legs_desc', '')}. Description: {trade.get('description', '')}",
                    "created_at": time.time()
                }
                storage.save_journal_entry(journal_entry)
                count += 1

            return jsonify({"success": True, "count": count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # API Route for Analysis (Audit)
    @app.route("/analyze", methods=["POST"])
    def analyze():
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

        try:
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

            if res.get("excel_report"):
                storage = get_storage_provider(app)
                storage.save_report(token, "report.xlsx", res["excel_report"].getvalue())

            username = session.get('username')
            if username and "error" not in res:
                to_save = res.copy()
                if "excel_report" in to_save:
                    del to_save["excel_report"]

                to_save["saved_at"] = datetime.now().isoformat()
                to_save["token"] = token
                to_save["style"] = style

                storage = get_storage_provider(app)
                storage.save_portfolio(username, json.dumps(to_save).encode('utf-8'))

            if "excel_report" in res:
                del res["excel_report"] # Can't JSON serialize bytes

            res["token"] = token
            return jsonify(res)

        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/download/<token>/<filename>")
    def download(token: str, filename: str):
        storage = get_storage_provider(app)
        data = storage.get_report(token, filename)

        if not data:
             return "File not found", 404
        
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename
        )

    # Serve React App
    @app.route("/", defaults={'path': ''})
    @app.route("/<path:path>")
    def catch_all(path):
        # Allow requests to API routes or static files to pass through
        if path.startswith("api/") or path.startswith("static/") or path.startswith("download/"):
            return "Not Found", 404

        # Check if the requested file exists in the react build directory
        build_dir = os.path.join(app.static_folder, "react_build")
        if path != "" and os.path.exists(os.path.join(build_dir, path)):
            return send_from_directory(build_dir, path)

        # Otherwise serve index.html
        return send_from_directory(build_dir, "index.html")

    return app

app = create_app()

if __name__ == "__main__":
    enable_https = os.environ.get("ENABLE_HTTPS", "0") == "1"
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"

    if enable_https:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode, ssl_context="adhoc")
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)
