from __future__ import annotations

import io
import os
import uuid
import threading
import time
import json
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify

from option_auditor import analyze_csv, screener, journal_analyzer
from option_auditor.main_analyzer import refresh_dashboard_data
from datetime import datetime, timedelta
from webapp.storage import get_storage_provider
from webapp.tasks import analyze_csv_task

# Cleanup interval in seconds
CLEANUP_INTERVAL = 1200 # 20 minutes
# Max age of reports in seconds
MAX_REPORT_AGE = 1200 # 20 minutes

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
    app = Flask(__name__, instance_relative_config=True)
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

    # Initialize Storage (Schema) on Startup
    # This prevents race conditions or repeated checks during requests.
    with app.app_context():
        try:
            storage = get_storage_provider(app)
            if hasattr(storage, 'initialize'):
                storage.initialize()
        except Exception as e:
            print(f"Startup Warning: Storage initialization failed: {e}")

    if not testing and (not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
        t = threading.Thread(target=cleanup_job, args=(app,), daemon=True)
        t.start()

    ALLOWED_EXTENSIONS = {".csv"}

    def _allowed_filename(filename: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        return ext in ALLOWED_EXTENSIONS

    @app.after_request
    def add_security_headers(response):
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
        return render_template("error.html", message="Upload too large. Max size is limited."), 413

    @app.before_request
    def ensure_guest_session():
        # Ensure every visitor has a username (UUID) for storage keyed by username
        if 'username' not in session:
            session['username'] = f"guest_{uuid.uuid4().hex}"
            session.permanent = True

    @app.route("/feedback", methods=["POST"])
    def feedback():
        message = request.form.get("message", "").strip()
        username = session.get("username", "Anonymous")

        if message:
            storage = get_storage_provider(app)
            try:
                storage.save_feedback(username, message)
                flash("Thank you for your feedback!", "success")
            except Exception as e:
                flash("Failed to submit feedback. Please try again.", "error")
                print(f"Feedback error: {e}")
        else:
            flash("Feedback message cannot be empty.", "warning")

        return redirect(request.referrer or url_for('index'))

    @app.route("/dashboard")
    def dashboard():
        username = session.get('username')
        # Username is guaranteed by before_request, but let's be safe
        if not username:
             return redirect(url_for('index'))

        storage = get_storage_provider(app)
        data_bytes = storage.get_portfolio(username)

        if not data_bytes:
            flash("No saved portfolio found. Please upload a CSV first.", "info")
            return redirect(url_for('index'))

        try:
            saved_data = json.loads(data_bytes)

            # Refresh with Live Data
            updated_data = refresh_dashboard_data(saved_data)

            # Add display metadata
            last_saved = "Unknown"
            if "saved_at" in updated_data:
                try:
                    dt = datetime.fromisoformat(updated_data["saved_at"])
                    last_saved = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass

            return render_template(
                "results.html",
                dashboard_mode=True,
                last_updated=last_saved,
                token=updated_data.get("token", uuid.uuid4().hex),
                style=updated_data.get("style", "income"),
                **updated_data
            )
        except Exception as e:
            return render_template("error.html", message=f"Failed to load dashboard: {e}")

    @app.route("/health")
    def health():
        return "OK", 200

    @app.route("/", methods=["GET"])
    def index():
        username = session.get('username')
        has_portfolio = False
        if username:
            storage = get_storage_provider(app)
            if storage.get_portfolio(username):
                has_portfolio = True
        return render_template("upload.html", has_portfolio=has_portfolio)

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

    @app.route("/screen", methods=["POST"])
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

        try:
            results = screener.screen_market(iv_rank, rsi_threshold, time_frame)
            sector_results = screener.screen_sectors(iv_rank, rsi_threshold, time_frame)
            return render_template("screener_results.html", results=results, sector_results=sector_results, iv_rank_threshold=iv_rank, rsi_threshold=rsi_threshold, time_frame=time_frame)
        except Exception as e:
            return render_template("error.html", message=f"Screener failed: {e}")

    @app.route("/screen/turtle", methods=["GET"])
    def screen_turtle():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_turtle_setups(ticker_list=ticker_list, time_frame=time_frame)
            return render_template("turtle_results.html", results=results)
        except Exception as e:
            return render_template("error.html", message=f"Turtle Screener failed: {e}")

    @app.route("/screen/ema", methods=["GET"])
    def screen_ema():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()

            results = screener.screen_5_13_setups(ticker_list=ticker_list, time_frame=time_frame)
            return render_template("ema_results.html", results=results)
        except Exception as e:
            return render_template("error.html", message=f"EMA Screener failed: {e}")

    @app.route("/job_status/<task_id>")
    def job_status(task_id):
        task = analyze_csv_task.AsyncResult(task_id)
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'status': 'Processing...'
            }
        elif task.state == 'PROCESSING':
            response = {
                'state': task.state,
                'status': 'Analyzing data...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'status': 'Complete',
                'result': task.result
            }
        else:
            response = {
                'state': task.state,
                'status': str(task.info)
            }
        return jsonify(response)

    @app.route("/processing/<task_id>")
    def processing(task_id):
        return render_template("processing.html", task_id=task_id)

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

        had_error = False
        def _to_float(name: str) -> Optional[float]:
            nonlocal had_error
            val = request.form.get(name, "").strip()
            if val:
                try:
                    return float(val)
                except ValueError:
                    flash(f"{name.replace('_', ' ').title()} must be a number.", "warning")
                    had_error = True
            return None

        account_size_start = _to_float("account_size_start")
        net_liquidity_now = _to_float("net_liquidity_now")
        buying_power_available_now = _to_float("buying_power_available_now")
        style = request.form.get("style", "income")
        fee_per_trade = _to_float("fee_per_trade")
        csv_fee_per_trade = _to_float("csv_fee_per_trade")

        if had_error:
            return redirect(url_for("index"))

        if (not file or file.filename == "") and not manual_data:
            flash("Please choose a CSV file or enter trades manually.", "warning")
            return redirect(url_for("index"))

        if file and file.filename != "" and not _allowed_filename(file.filename):
            flash("Only .csv files are allowed", "warning")
            return redirect(url_for("index"))

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
        elif date_mode == "range":
            if not start_date or not end_date:
                flash("Please select both start and end dates or choose 'All data'", "warning")
                return redirect(url_for("index"))

        token = uuid.uuid4().hex
        
        final_global_fees = fee_per_trade if manual_data else csv_fee_per_trade
        username = session.get('username')

        # Async Flow (SaaS mode check)
        storage = get_storage_provider(app)
        # We can detect if we should use Celery by checking if we are using SaaSStorage
        # or just if CELERY_BROKER_URL is set in env.
        # But `webapp/tasks.py` is always imported.

        # We generally only want async if explicitly configured or if we are in SaaS mode.
        # However, testing environments might trigger this if we check hasattr(storage, 'save_upload').
        # So let's check if we are NOT testing, or if CELERY_BROKER_URL is explicitly set.

        is_async = (os.environ.get("CELERY_BROKER_URL") is not None) and (not app.config["TESTING"])

        # Prepare Options for Task
        options = {
            "broker": broker,
            "account_size_start": account_size_start,
            "net_liquidity_now": net_liquidity_now,
            "buying_power_available_now": buying_power_available_now,
            "style": style,
            "global_fees": final_global_fees,
            "start_date": start_date,
            "end_date": end_date,
            "manual_data": manual_data,
            "token": token,
            "username": username
        }

        if is_async and file and file.filename != "":
             # Upload to storage (S3 or DB) first
             try:
                 file_data = file.read()
                 storage.save_upload(token, file_data)

                 # Dispatch Task
                 task = analyze_csv_task.delay(token, options)

                 return redirect(url_for('processing', task_id=task.id))

             except Exception as e:
                 # If async dispatch fails, we return error.
                 # We no longer gracefully fallback to sync because 'save_upload' is expected to work if is_async is True.
                 # However, to be robust, we could log and error out.
                 return render_template("error.html", message=f"Failed to initiate background job: {e}")

        # Sync Flow (Legacy / Local / Fallback)
        csv_path = None
        if file and file.filename != "":
            # In-memory processing (re-read if needed, but file.read() consumes it)
            # file_data is only present if we tried async and failed or just read it?
            # Actually, if is_async was true, we either returned redirect or error.
            # So if we are here, is_async is false.
            csv_path = io.StringIO(file.read().decode('utf-8'))

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
                storage.save_report(token, "report.xlsx", res["excel_report"].getvalue())

            # Save for Persistence
            if username and "error" not in res:
                to_save = res.copy()
                if "excel_report" in to_save:
                    del to_save["excel_report"]

                to_save["saved_at"] = datetime.now().isoformat()
                to_save["token"] = token
                to_save["style"] = style

                storage.save_portfolio(username, json.dumps(to_save).encode('utf-8'))

        except Exception as exc:
            return render_template("error.html", message=f"Failed to analyze data: {exc}")

        if "error" in res:
            return render_template("error.html", message=f"Failed to analyze: {res['error']}")

        return render_template(
            "results.html",
            token=token,
            style=style,
            **res
        )

    @app.route("/download/<token>/<filename>")
    def download(token: str, filename: str):
        storage = get_storage_provider(app)
        data = storage.get_report(token, filename)

        if not data:
             return render_template("error.html", message="Download link expired or invalid."), 404
        
        return send_file(
            io.BytesIO(data),
            as_attachment=True,
            download_name=filename
        )

    return app

app = create_app()

if __name__ == "__main__":
    enable_https = os.environ.get("ENABLE_HTTPS", "0") == "1"
    if enable_https:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True, ssl_context="adhoc")
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
