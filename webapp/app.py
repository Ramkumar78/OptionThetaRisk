from __future__ import annotations

import io
import os
import shutil
import uuid
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

from option_auditor import analyze_csv
from datetime import datetime, timedelta


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Basic, non-secret key for session/flash in dev; override via env in prod
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(16))
    # Limit uploads to 5 MB by default
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    # Define a folder for storing reports
    app.config["REPORT_FOLDER"] = os.path.join(app.instance_path, 'reports')
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)

    ALLOWED_EXTENSIONS = {".csv"}

    def _allowed_filename(filename: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        return ext in ALLOWED_EXTENSIONS

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

        if not file or file.filename == "":
            flash("Please choose a CSV file", "warning")
            return redirect(url_for("index"))

        if not _allowed_filename(file.filename):
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
        # Create a dedicated directory for this request's input and output
        request_dir = os.path.join(app.config['REPORT_FOLDER'], token)
        os.makedirs(request_dir, exist_ok=True)
        
        csv_path = os.path.join(request_dir, "upload.csv")
        file.save(csv_path)

        try:
            res = analyze_csv(
                csv_path,
                broker=broker,
                account_size_start=account_size_start,
                net_liquidity_now=net_liquidity_now,
                buying_power_available_now=buying_power_available_now,
                out_dir=request_dir, # Save reports in the same request-specific folder
                report_format="all",
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc: # pragma: no cover
            shutil.rmtree(request_dir, ignore_errors=True)
            return render_template("error.html", message=f"Failed to analyze CSV: {exc}")

        if "error" in res:
            shutil.rmtree(request_dir, ignore_errors=True)
            return render_template("error.html", message=f"Failed to analyze CSV: {res['error']}")

        return render_template(
            "results.html",
            token=token,
            **res
        )

    @app.route("/download/<token>/<filename>")
    def download(token: str, filename: str):
        # Securely serve files from the request-specific report directory
        directory = os.path.join(app.config['REPORT_FOLDER'], token)
        if not os.path.isdir(directory):
             return render_template("error.html", message="Download link expired or invalid."), 404
        
        return send_from_directory(
            directory,
            filename,
            as_attachment=True
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
