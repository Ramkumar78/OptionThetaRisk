from __future__ import annotations

import io
import os
import tempfile
import uuid
from typing import Dict

from flask import Flask, render_template, request, redirect, url_for, send_file, flash

from option_auditor import analyze_csv
from datetime import datetime, timedelta


def create_app() -> Flask:
    app = Flask(__name__)
    # Basic, non-secret key for session/flash in dev; override via env in prod
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(16))
    # Limit uploads to 5 MB by default
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))

    ALLOWED_EXTENSIONS = {".csv"}

    # In-memory store for generated files, keyed by token
    STORE: Dict[str, Dict[str, bytes]] = {}

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
        account_size_raw = request.form.get("account_size", "").strip()
        account_size = None
        if account_size_raw:
            try:
                account_size = float(account_size_raw)
            except ValueError:
                flash("Account size must be a number", "warning")
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

        # Convert presets to actual dates (inclusive). Use simple day approximations for months/years.
        now = datetime.now()
        if date_mode in {"7d", "14d", "1m", "6m", "1y", "2y", "ytd"}:
            if date_mode == "7d":
                s_dt = now - timedelta(days=7)
            elif date_mode == "14d":
                s_dt = now - timedelta(days=14)
            elif date_mode == "1m":
                s_dt = now - timedelta(days=30)
            elif date_mode == "6m":
                s_dt = now - timedelta(days=182)
            elif date_mode == "1y":
                s_dt = now - timedelta(days=365)
            elif date_mode == "2y":
                s_dt = now - timedelta(days=730)
            else:  # ytd
                s_dt = datetime(now.year, 1, 1)
            start_date = s_dt.date().isoformat()
            end_date = now.date().isoformat()
        elif date_mode == "range":
            if not start_date or not end_date:
                flash("Please select both start and end dates or choose 'All data'", "warning")
                return redirect(url_for("index"))

        # Save upload to a temporary file safely
        tmpdir = tempfile.mkdtemp(prefix="opt_audit_")
        csv_path = os.path.join(tmpdir, "upload.csv")
        file.save(csv_path)

        # Run analysis, writing outputs into the same temp dir
        try:
            res = analyze_csv(
                csv_path,
                broker=broker,
                account_size=account_size,
                out_dir=tmpdir,
                report_format="all",
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc: # pragma: no cover
            # Show a friendly error; do not leak stack traces by default
            return render_template("error.html", message=f"Failed to analyze CSV: {exc}")

        if "error" in res:
            return render_template("error.html", message=f"Failed to analyze CSV: {res['error']}")

        # Read generated files into memory for download endpoints
        trades_bytes = b""
        report_bytes = b""
        trades_fp = os.path.join(tmpdir, "trades.csv")
        report_fp = os.path.join(tmpdir, "report.xlsx")
        if os.path.exists(trades_fp):
            with open(trades_fp, "rb") as f:
                trades_bytes = f.read()
        if os.path.exists(report_fp):
            with open(report_fp, "rb") as f:
                report_bytes = f.read()

        # Clean up temp directory content after loading into memory
        try:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception: # pragma: no cover
            pass

        token = uuid.uuid4().hex
        STORE[token] = {
            "trades_csv": trades_bytes,
            "report_xlsx": report_bytes,
        }

        return render_template(
            "results.html",
            token=token,
            broker=res.get("broker"),
            metrics=res.get("metrics", {}),
            verdict=res.get("verdict"),
            max_exposure=res.get("max_exposure", 0.0),
            account_size=account_size,
            symbols=res.get("symbols", []),
            strategy_groups=res.get("strategy_groups", []),
            open_positions=res.get("open_positions", []),
            date_window=res.get("date_window"),
        )

    @app.route("/download/<token>/<kind>")
    def download(token: str, kind: str):
        item = STORE.get(token)
        if not item:
            return render_template("error.html", message="Download link expired. Please re-run the analysis."), 404
        if kind == "trades.csv":
            data = item.get("trades_csv") or b""
            return send_file(io.BytesIO(data), as_attachment=True, download_name="trades.csv", mimetype="text/csv")
        if kind == "report.xlsx":
            data = item.get("report_xlsx") or b""
            return send_file(
                io.BytesIO(data),
                as_attachment=True,
                download_name="report.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return render_template("error.html", message="Unknown file requested."), 400

    return app


app = create_app()

if __name__ == "__main__":  # pragma: no cover
    # Dev server
    enable_https = os.environ.get("ENABLE_HTTPS", "0") == "1"
    if enable_https:
        # Ad-hoc self-signed certificate for local development
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True, ssl_context="adhoc")
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
