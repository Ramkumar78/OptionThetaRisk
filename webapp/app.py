from __future__ import annotations

import io
import os
import uuid
import threading
import time
import json
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash

from option_auditor import analyze_csv, screener
from option_auditor.main_analyzer import refresh_dashboard_data
from datetime import datetime, timedelta
from webapp.storage import get_storage_provider

# Cleanup interval in seconds
CLEANUP_INTERVAL = 3600 # 1 hour
# Max age of reports in seconds
MAX_REPORT_AGE = 3600 # 1 hour
ADMIN_EMAIL = "shriram2222@gmail.com"

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

def send_email_background(subject, body, to_email):
    """Sends an email in the background using smtplib."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        print(f"[Mock Email] To: {to_email} | Subject: {subject} | Body: {body}")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_email_async(subject, body, to_email=ADMIN_EMAIL):
    t = threading.Thread(target=send_email_background, args=(subject, body, to_email))
    t.start()

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
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

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
    def require_login():
        # Allow static files and the login/register route
        if request.endpoint in ['login', 'register', 'static', 'favicon']:
            return

        # Check if user is logged in
        if 'username' not in session:
            return redirect(url_for('login'))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            location = request.form.get("location", "").strip()
            experience = request.form.get("trading_experience", "").strip()

            if not username or not password:
                flash("Username and password are required.", "error")
                return render_template("register.html")

            storage = get_storage_provider(app)
            if storage.get_user(username):
                flash("Username already exists.", "error")
                return render_template("register.html")

            user_data = {
                "username": username,
                "password_hash": generate_password_hash(password),
                "first_name": first_name,
                "last_name": last_name,
                "location": location,
                "trading_experience": experience,
                "created_at": time.time(),
                "last_login": time.time()
            }

            try:
                storage.save_user(user_data)

                # Notify Admin
                send_email_async(
                    subject=f"New User Registration: {username}",
                    body=f"User: {first_name} {last_name} ({username})\nLocation: {location}\nExperience: {experience}\nTime: {datetime.now()}",
                    to_email=ADMIN_EMAIL
                )

                flash("Registration successful! Please login.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                flash(f"Error creating account: {e}", "error")

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if username and password:
                storage = get_storage_provider(app)
                user = storage.get_user(username)

                if user and check_password_hash(user['password_hash'], password):
                    session['username'] = username
                    session.permanent = True

                    # Update login time
                    user['last_login'] = time.time()
                    storage.save_user(user) # Update

                    return redirect(url_for('index'))
                else:
                    flash("Invalid username or password.", "error")
            else:
                flash("Please enter both username and password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop('username', None)
        return redirect(url_for('login'))

    @app.route("/feedback", methods=["POST"])
    def feedback():
        message = request.form.get("message", "").strip()
        username = session.get("username", "Anonymous")

        if message:
            storage = get_storage_provider(app)
            try:
                storage.save_feedback(username, message)
                send_email_async(
                    subject=f"New Feedback from {username}",
                    body=f"User: {username}\n\nMessage:\n{message}",
                    to_email=ADMIN_EMAIL
                )
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
        if not username:
            return redirect(url_for('login'))

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

    @app.route("/", methods=["GET"])
    def index():
        username = session.get('username')
        has_portfolio = False
        if username:
            storage = get_storage_provider(app)
            if storage.get_portfolio(username):
                has_portfolio = True
        return render_template("upload.html", has_portfolio=has_portfolio)

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
        
        csv_path = None
        if file and file.filename != "":
            # In-memory processing
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

            # Save for Persistence
            username = session.get('username')
            if username and "error" not in res:
                to_save = res.copy()
                if "excel_report" in to_save:
                    del to_save["excel_report"]

                to_save["saved_at"] = datetime.now().isoformat()
                # Persist token and style too
                to_save["token"] = token
                to_save["style"] = style

                storage = get_storage_provider(app)
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
