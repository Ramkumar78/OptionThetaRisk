from __future__ import annotations

import io
import os
import shutil
import uuid
import threading
import time
import json
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, send_file

from option_auditor import analyze_csv
from datetime import datetime, timedelta
from webapp.storage import get_storage_provider

# Cleanup interval in seconds
CLEANUP_INTERVAL = 3600 # 1 hour
# Max age of reports in seconds
MAX_REPORT_AGE = 3600 # 1 hour

def cleanup_job(app):
    """Background thread to clean up old reports."""
    # We need an app context or storage provider reference
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

    # Basic, non-secret key for session/flash in dev; override via env in prod
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(16))
    # Limit uploads to 5 MB by default
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))

    # Start cleanup thread only if not testing
    # And only in main process (reloader protection)
    if not testing and (not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
        t = threading.Thread(target=cleanup_job, args=(app,), daemon=True)
        t.start()

    ALLOWED_EXTENSIONS = {".csv"}

    def _allowed_filename(filename: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        return ext in ALLOWED_EXTENSIONS

    @app.after_request
    def add_security_headers(response):
        # Basic Content-Security-Policy
        # Allow default self, Bootstrap CDN (will replace), Tailwind CDN, HTMX, etc.
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "object-src 'none';"
        )
        return response

    @app.errorhandler(413)
    def too_large(e):  # pragma: no cover
        return render_template("error.html", message="Upload too large. Max size is limited."), 413

    @app.route("/", methods=["GET"])
    def index():
        return render_template("upload.html")

    @app.route("/analyze", methods=["POST"])
    def analyze():
        file = request.files.get("csv")
        broker = request.form.get("broker", "auto")
        
        # Check if manual data was submitted
        manual_data_json = request.form.get("manual_trades")
        manual_data = None
        if manual_data_json:
            try:
                manual_data = json.loads(manual_data_json)
                if manual_data and isinstance(manual_data, list):
                    # Filter out empty rows if any
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

        if had_error:
            return redirect(url_for("index"))

        # If no CSV and no Manual Data, complain
        if (not file or file.filename == "") and not manual_data:
            flash("Please choose a CSV file or enter trades manually.", "warning")
            return redirect(url_for("index"))

        if file and file.filename != "" and not _allowed_filename(file.filename):
            flash("Only .csv files are allowed", "warning")
            return redirect(url_for("index"))

        # Read date-range selection
        date_mode = request.form.get("date_mode", "all")
        start_date = request.form.get("start_date", "").strip() or None
        end_date = request.form.get("end_date", "").strip() or None

        # Convert presets to actual dates (inclusive).
        now = datetime.now()
        if date_mode in {"7d", "14d", "1m", "6m", "1y", "2y", "ytd"}:
            if date_mode == "7d": s_dt = now - timedelta(days=7)
            elif date_mode == "14d": s_dt = now - timedelta(days=14)
            elif date_mode == "1m": s_dt = now - timedelta(days=30)
            elif date_mode == "6m": s_dt = now - timedelta(days=182)
            elif date_mode == "1y": s_dt = now - timedelta(days=365)
            elif date_mode == "2y": s_dt = now - timedelta(days=730)
            else: s_dt = datetime(now.year, 1, 1) # ytd
            start_date = s_dt.date().isoformat()
            end_date = now.date().isoformat()
        elif date_mode == "range":
            if not start_date or not end_date:
                flash("Please select both start and end dates or choose 'All data'", "warning")
                return redirect(url_for("index"))

        # Generate a unique ID for this analysis request
        token = uuid.uuid4().hex
        
        # Create a temp directory for processing
        temp_dir = os.path.join(app.instance_path, 'temp_' + token)
        os.makedirs(temp_dir, exist_ok=True)

        csv_path = None
        if file and file.filename != "":
            csv_path = os.path.join(temp_dir, "upload.csv")
            file.save(csv_path)

        try:
            res = analyze_csv(
                csv_path=csv_path,
                broker=broker,
                account_size_start=account_size_start,
                net_liquidity_now=net_liquidity_now,
                buying_power_available_now=buying_power_available_now,
                out_dir=temp_dir,
                report_format="all",
                start_date=start_date,
                end_date=end_date,
                manual_data=manual_data
            )

            # If successful, check for report.xlsx and store using StorageProvider
            report_path = os.path.join(temp_dir, "report.xlsx")
            if os.path.exists(report_path):
                with open(report_path, "rb") as f:
                    file_data = f.read()

                storage = get_storage_provider(app)
                storage.save_report(token, "report.xlsx", file_data)

        except Exception as exc: # pragma: no cover
            shutil.rmtree(temp_dir, ignore_errors=True)
            return render_template("error.html", message=f"Failed to analyze data: {exc}")
        finally:
            # Cleanup temp dir immediately
            shutil.rmtree(temp_dir, ignore_errors=True)

        if "error" in res:
            return render_template("error.html", message=f"Failed to analyze: {res['error']}")

        return render_template(
            "results.html",
            token=token,
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

if __name__ == "__main__":  # pragma: no cover
    # Dev server
    enable_https = os.environ.get("ENABLE_HTTPS", "0") == "1"
    if enable_https:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True, ssl_context="adhoc")
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
