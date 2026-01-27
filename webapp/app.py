from __future__ import annotations

import io
import os
import uuid
import threading
import time
import json
import logging
import sys
from typing import Optional
from collections import OrderedDict

import pandas as pd
import yfinance as yf
from flask import Flask, request, redirect, url_for, flash, send_file, session, jsonify, send_from_directory, g

from option_auditor import analyze_csv, screener, journal_analyzer, portfolio_risk
from option_auditor.main_analyzer import refresh_dashboard_data
from option_auditor.uk_stock_data import get_uk_tickers
from option_auditor.us_stock_data import get_united_states_stocks
from option_auditor.master_screener import screen_master_convergence
from option_auditor.sp500_data import get_sp500_tickers
from option_auditor.common.constants import LIQUID_OPTION_TICKERS, SECTOR_COMPONENTS, DEFAULT_ACCOUNT_SIZE
from option_auditor.unified_backtester import UnifiedBacktester

# Import Strategies
from option_auditor.strategies.isa import IsaStrategy
from option_auditor.strategies.turtle import TurtleStrategy
from option_auditor.common.data_utils import get_cached_market_data
from option_auditor.common.screener_utils import resolve_region_tickers
# from option_auditor.unified_screener import screen_universal_dashboard

# Import Data Lists
from option_auditor.sp500_data import SP500_TICKERS
from option_auditor.uk_stock_data import get_uk_tickers
from option_auditor.india_stock_data import INDIA_TICKERS

# Import India Data (Compat)
try:
    from option_auditor.india_stock_data import INDIAN_TICKERS_RAW
except ImportError:
    INDIAN_TICKERS_RAW = []
from datetime import datetime, timedelta
from webapp.storage import get_storage_provider as _get_storage_provider
import resend
from dotenv import load_dotenv
from option_auditor.common.resilience import data_api_breaker

# Load environment variables from .env file
load_dotenv()

# Cleanup interval in seconds
CLEANUP_INTERVAL = 1200 # 20 minutes
# Max age of reports in seconds
MAX_REPORT_AGE = 1200 # 20 minutes

# --- MEMORY SAFE CACHE (LRU) ---
class LRUCache:
    def __init__(self, capacity: int, ttl_seconds: int):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl_seconds

    def get(self, key):
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check Expiry
        if time.time() - timestamp > self.ttl:
            self.cache.pop(key)
            return None

        # Move to end (Recently Used)
        self.cache.move_to_end(key)
        return value

    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        self.cache.move_to_end(key)

        # Evict if full
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

# Init Cache (Max 50 results, 10 min expiry)
screener_cache = LRUCache(capacity=50, ttl_seconds=600)

def get_cached_screener_result(key):
    return screener_cache.get(key)

def cache_screener_result(key, data):
    screener_cache.set(key, data)

# Cached storage provider singleton at application level (if appropriate)
# Since we might rely on app context (e.g. SQLite path), we use Flask's `g` or memoize based on app instance.
# But `get_storage_provider` in `storage.py` is a factory.
# We will wrap it here to memoize within the app context or request.

def get_storage_provider(app):
    """
    Wrapper to get storage provider.
    Uses Flask 'g' to cache per-request, but since we refactored DatabaseStorage to cache engine internally,
    creating a new DatabaseStorage object is cheap.
    However, using 'g' is still better to avoid re-initializing the object repeatedly in one request.
    """
    if 'storage_provider' not in g:
        g.storage_provider = _get_storage_provider(app)
    return g.storage_provider

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
                # Regex to find specific key pattern: key=${key:-(.*?)}
                # Handles lines like: - SMTP_USER=${SMTP_USER:-tradeauditor9@gmail.com}
                import re
                match = re.search(fr"{key}=\${{{key}:-(.*?)}}", content)
                if match:
                    return match.group(1)
    except Exception:
        pass  # Fallback to default if regex fails

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
        # Here we don't have 'g', so we call factory directly.
        # But 'DatabaseStorage' now caches engine, so it's cheap.
        storage = _get_storage_provider(app)
        while True:
            try:
                storage.cleanup_old_reports(MAX_REPORT_AGE)
            except Exception as e:
                app.logger.error(f"Cleanup job failed: {e}")
            time.sleep(CLEANUP_INTERVAL)

def create_app(testing: bool = False) -> Flask:
    # --- LOGGING CONFIGURATION ---
    # Configure root logger to output to stdout with format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    app = Flask(__name__, instance_relative_config=True, static_folder="static")

    # Ensure app logger propagates to root logger
    app.logger.setLevel(logging.INFO)

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
        app.logger.warning("Upload rejected: Too large.")
        return jsonify({"error": "Upload too large. Max size is limited."}), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal Server Error")
        return jsonify({"error": "Internal Server Error"}), 500

    @app.before_request
    def ensure_guest_session():
        # Ensure every visitor has a username (UUID) for storage keyed by username
        if 'username' not in session:
            session['username'] = f"guest_{uuid.uuid4().hex}"
            session.permanent = True
            app.logger.info(f"New guest session created: {session['username']}")

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

                app.logger.info(f"Feedback received from {username}")
                return jsonify({"success": True, "message": "Feedback submitted"})
            except Exception as e:
                app.logger.error(f"Feedback error: {e}")
                return jsonify({"error": "Failed to submit feedback"}), 500
        else:
            return jsonify({"error": "Message cannot be empty"}), 400

    @app.route("/dashboard")
    def dashboard():
        username = session.get('username')
        if not username:
             return jsonify({"error": "No session"}), 401

        app.logger.info(f"Dashboard access by {username}")
        storage = get_storage_provider(app)
        data_bytes = storage.get_portfolio(username)

        if not data_bytes:
            return jsonify({"error": "No portfolio found"})

        try:
            saved_data = json.loads(data_bytes)
            updated_data = refresh_dashboard_data(saved_data)
            app.logger.info(f"Dashboard data refreshed for {username}")
            return jsonify(updated_data)
        except Exception as e:
            app.logger.error(f"Dashboard refresh error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/health")
    def health():
        return "OK", 200

    @app.route("/api/screener/status")
    def get_breaker_status():
        """
        Returns the real-time status of the Circuit Breaker.
        Used by the frontend to display 'Stale Data' warnings.
        """
        return jsonify({
            "api_health": data_api_breaker.current_state, # 'closed', 'open', 'half-open'
            "is_fallback": data_api_breaker.current_state == 'open'
        })

    @app.route('/backtest/run', methods=['GET'])
    def run_backtest():
        ticker = request.args.get('ticker')
        strategy = request.args.get('strategy', 'master') # master, turtle, isa

        app.logger.info(f"Starting backtest: {strategy} on {ticker}")

        if not ticker:
            return jsonify({"error": "Ticker required"}), 400

        try:
            backtester = UnifiedBacktester(ticker, strategy_type=strategy)
            result = backtester.run()
            app.logger.info(f"Backtest completed for {ticker}")
            return jsonify(result)
        except Exception as e:
            app.logger.exception(f"Backtest Failed: {e}")
            return jsonify({"error": str(e)}), 500

    # API Routes for Screener
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
        region = request.form.get("region", "us")

        app.logger.info(f"Screen request: region={region}, time={time_frame}")

        cache_key = ("market", iv_rank, rsi_threshold, time_frame, region)
        cached = get_cached_screener_result(cache_key)
        if cached:
            app.logger.info("Serving cached screen result")
            return jsonify(cached)

        try:
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

            app.logger.info(f"Screen completed. Results: {count}")
            if count == 0:
                app.logger.warning("Screen returned 0 results.")

            return jsonify(data)
        except Exception as e:
            app.logger.exception(f"Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/screen/turtle', methods=['GET'])
    def screen_turtle():
        region = request.args.get('region', 'us')
        time_frame = request.args.get('time_frame', '1d')
        app.logger.info(f"Turtle Screen request: region={region}")

        try:
            results = screener.screen_turtle_setups(region=region, time_frame=time_frame)
            app.logger.info(f"Turtle Screen completed. Results: {len(results)}")
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Turtle Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/isa/check", methods=["GET"])
    def check_isa_stock():
        try:
            query = request.args.get("ticker", "").strip()
            if not query:
                return jsonify({"error": "No ticker provided"}), 400

            app.logger.info(f"ISA Check request for {query}")

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
                app.logger.warning(f"ISA Check: No data found for {ticker}")
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

            app.logger.info(f"ISA Check result for {ticker}: {result.get('signal')}")
            return jsonify(result)
        except Exception as e:
            app.logger.exception(f"ISA Check Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/alpha101", methods=["GET"])
    def screen_alpha101():
        try:
            region = request.args.get("region", "us")
            time_frame = request.args.get("time_frame", "1d")
            app.logger.info(f"Alpha 101 Screen request: region={region}, time_frame={time_frame}")

            cache_key = ("alpha101", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            # Use the new function
            results = screener.screen_alpha_101(region=region, time_frame=time_frame)

            app.logger.info(f"Alpha 101 Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Alpha 101 Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/mystrategy", methods=["GET"])
    def screen_my_strategy_route():
        try:
            region = request.args.get("region", "us")
            app.logger.info(f"MyStrategy Screen request: region={region}")

            cache_key = ("mystrategy", region)
            # Optional: Use caching if you implement it broadly
            cached = get_cached_screener_result(cache_key)
            if cached: return jsonify(cached)

            results = screener.screen_my_strategy(region=region)

            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"MyStrategy Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/fortress", methods=["GET"])
    def screen_fortress():
        try:
            time_frame = request.args.get("time_frame", "1d")
            app.logger.info(f"Fortress Screen request: time_frame={time_frame}")
            cache_key = ("api_screen_fortress_us", time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached: return jsonify(cached)

            results = screener.screen_dynamic_volatility_fortress(time_frame=time_frame)

            app.logger.info(f"Fortress Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Fortress Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/options_only", methods=["GET"])
    def screen_options_only():
        try:
            app.logger.info("Thalaiva Options Only Screen Initiated")

            # Cache Key
            cache_key = ("options_only_scanner", "us")
            cached = get_cached_screener_result(cache_key)
            if cached:
                app.logger.info("Serving cached Options Only results")
                return jsonify(cached)

            # Run with limit=75 to be safe
            results = screener.screen_options_only_strategy(limit=75)

            # Cache results
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.error(f"Critical Screener Error: {e}")
            return jsonify({"error": "Scanner Timeout or Error"}), 500

    @app.route('/screen/isa', methods=['GET'])
    def screen_isa():
        region = request.args.get('region', 'us')
        time_frame = request.args.get('time_frame', '1d')
        app.logger.info(f"ISA Screen request: region={region}, time_frame={time_frame}")

        # Position Sizing Param (Default £76k)
        account_size = DEFAULT_ACCOUNT_SIZE
        acc_size_str = request.args.get("account_size", "").strip()
        if acc_size_str:
            try:
                account_size = float(acc_size_str)
            except ValueError:
                pass

        # Check result cache first (Note: caching ignores custom account size for now, assumes default or user refreshes)
        # To strictly support custom sizing per user, we should include account_size in cache key
        # or calculate sizing on the fly after fetching.
        # For simplicity/performance, we bind it to the cache key if provided different than default?
        # Actually, let's keep it simple: Cache Key includes account size if non-standard?
        # If the user changes account size, they expect new numbers.

        cache_key = ("isa", region, time_frame, account_size)
        cached = get_cached_screener_result(cache_key)
        if cached:
            app.logger.info("Serving cached ISA screen result")
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
        try:
            data = get_cached_market_data(tickers, period="2y", cache_name=cache_name)

            if data.empty:
                app.logger.warning("ISA Screen: Data empty")
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
                    # app.logger.warning(f"ISA Screen failed for {ticker}: {e}")
                    continue

            app.logger.info(f"ISA Screen completed. Results: {len(results)}")

            # Cache the successful result
            cache_screener_result(cache_key, results)

            return jsonify({"results": results})
        except Exception as e:
            app.logger.exception(f"ISA Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/bull_put", methods=["GET"])
    def screen_bull_put():
        try:
            region = request.args.get("region", "us")
            time_frame = request.args.get("time_frame", "1d")
            app.logger.info(f"Bull Put Screen request: region={region}, time_frame={time_frame}")

            cache_key = ("bull_put", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                 ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                 ticker_list = get_uk_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                 filtered_sp500 = screener._get_filtered_sp500(check_trend=True)
                 watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                 ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_bull_put_spreads(ticker_list=ticker_list, time_frame=time_frame)
            app.logger.info(f"Bull Put Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Bull Put Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/vertical_put", methods=["GET"])
    def screen_vertical_put():
        try:
            region = request.args.get("region", "us")
            app.logger.info(f"Vertical Put Screen request: region={region}")

            # Cache key
            cache_key = ("vertical_put_v2", region)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            # Call the new logic
            results = screener.screen_vertical_put_spreads(region=region)

            app.logger.info(f"Vertical Put Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Vertical Put Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/darvas", methods=["GET"])
    def screen_darvas():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")
            app.logger.info(f"Darvas Screen request: region={region}, tf={time_frame}")

            cache_key = ("darvas", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                filtered_sp500 = screener._get_filtered_sp500(check_trend=True)
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_darvas_box(ticker_list=ticker_list, time_frame=time_frame)
            app.logger.info(f"Darvas Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Darvas Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/ema", methods=["GET"])
    def screen_ema():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")
            app.logger.info(f"EMA Screen request: region={region}, tf={time_frame}")

            cache_key = ("ema", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                filtered_sp500 = screener._get_filtered_sp500(check_trend=True)
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_5_13_setups(ticker_list=ticker_list, time_frame=time_frame)
            app.logger.info(f"EMA Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"EMA Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/mms", methods=["GET"])
    def screen_mms():
        try:
            time_frame = request.args.get("time_frame", "1h")
            region = request.args.get("region", "us")
            app.logger.info(f"MMS Screen request: region={region}, tf={time_frame}")

            cache_key = ("mms", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                ticker_list = screener.SECTOR_COMPONENTS.get("WATCH", [])

            results = screener.screen_mms_ote_setups(ticker_list=ticker_list, time_frame=time_frame)
            app.logger.info(f"MMS Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"MMS Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/liquidity_grabs", methods=["GET"])
    def screen_liquidity_grabs():
        try:
            time_frame = request.args.get("time_frame", "1h")
            region = request.args.get("region", "us")
            app.logger.info(f"Liquidity Grab Screen request: region={region}, tf={time_frame}")

            cache_key = ("liquidity_grabs", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                ticker_list = screener.SECTOR_COMPONENTS.get("WATCH", [])

            results = screener.screen_liquidity_grabs(ticker_list=ticker_list, time_frame=time_frame, region=region)
            app.logger.info(f"Liquidity Grab Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Liquidity Grab Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/squeeze", methods=["GET"])
    def screen_squeeze():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")
            app.logger.info(f"Squeeze Screen request: region={region}, tf={time_frame}")

            cache_key = ("squeeze", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                # For squeeze, use S&P 500 filtered
                filtered_sp500 = screener._get_filtered_sp500(check_trend=False)
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_bollinger_squeeze(ticker_list=ticker_list, time_frame=time_frame, region=region)
            app.logger.info(f"Squeeze Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Squeeze Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/hybrid", methods=["GET"])
    def screen_hybrid():
        try:
            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")
            app.logger.info(f"Hybrid Screen request: region={region}, tf={time_frame}")

            cache_key = ("hybrid", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                raw_sp500 = screener.get_sp500_tickers()
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(raw_sp500 + watch_list))

            results = screener.screen_hybrid_strategy(ticker_list=ticker_list, time_frame=time_frame, region=region)
            app.logger.info(f"Hybrid Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Hybrid Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/screen/master', methods=['GET'])
    def screen_master():
        region = request.args.get('region', 'us')
        time_frame = request.args.get('time_frame', '1d')
        app.logger.info(f"Master Fortress Screen request: region={region}, time_frame={time_frame}")

        # The adapter handles the list logic internally based on region
        try:
            results = screen_master_convergence(region=region, time_frame=time_frame)

            # Ensure it returns a list directly, or wrap in dict if frontend expects {results: [...]}
            # Based on your previous code, it seems to handle both, but let's be safe:
            count = len(results)
            app.logger.info(f"Fortress Screen completed. Results: {count}")

            # Frontend often expects { "results": [...] } or just [...]
            # Let's standardise on the list for this specific route if the frontend grid handles it
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Master Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/screen/quant', methods=['GET'])
    def screen_quant():
        # Redirect Quant requests to the Fortress as well, since QuantMasterScreener (OpenBB) is broken
        return screen_master()

    @app.route("/screen/fourier", methods=["GET"])
    def screen_fourier():
        try:
            query = request.args.get("ticker", "").strip()
            if query:
                app.logger.info(f"Fourier Single request: {query}")
                ticker = screener.resolve_ticker(query)
                if not ticker:
                    ticker = query.upper()

                results = screener.screen_fourier_cycles(ticker_list=[ticker], time_frame="1d")
                if not results:
                     return jsonify({"error": f"No cycle data found for {ticker}"}), 404
                return jsonify(results[0])

            time_frame = request.args.get("time_frame", "1d")
            region = request.args.get("region", "us")
            app.logger.info(f"Fourier Screen request: region={region}, tf={time_frame}")

            cache_key = ("fourier", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                filtered_sp500 = screener._get_filtered_sp500(check_trend=False)
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_fourier_cycles(ticker_list=ticker_list, time_frame=time_frame)
            app.logger.info(f"Fourier Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Fourier Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/rsi_divergence", methods=["GET"])
    def screen_rsi_divergence():
        try:
            region = request.args.get("region", "us")
            time_frame = request.args.get("time_frame", "1d")
            app.logger.info(f"RSI Divergence Screen request: region={region}, tf={time_frame}")

            cache_key = ("rsi_divergence", region, time_frame)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                filtered_sp500 = screener._get_filtered_sp500(check_trend=False)
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(filtered_sp500 + watch_list))

            results = screener.screen_rsi_divergence(ticker_list=ticker_list, time_frame=time_frame, region=region)
            app.logger.info(f"RSI Divergence Screen completed. Results: {len(results)}")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"RSI Divergence Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/universal", methods=["GET"])
    def screen_universal():
        try:
            region = request.args.get("region", "us")
            app.logger.info(f"Universal Screen request: region={region}")

            cache_key = ("universal", region)
            cached = get_cached_screener_result(cache_key)
            if cached:
                return jsonify(cached)

            ticker_list = None
            if region == "uk_euro":
                ticker_list = screener.get_uk_euro_tickers()
            elif region == "uk":
                ticker_list = get_uk_tickers()
            elif region == "india":
                ticker_list = screener.get_indian_tickers()
            elif region == "united_states":
                ticker_list = get_united_states_stocks()
            elif region == "sp500":
                raw_sp500 = screener.get_sp500_tickers()
                watch_list = screener.SECTOR_COMPONENTS.get("WATCH", [])
                ticker_list = list(set(raw_sp500 + watch_list))

            results = screener.screen_universal_dashboard(ticker_list=ticker_list)
            app.logger.info(f"Universal Screen completed.")
            cache_screener_result(cache_key, results)
            return jsonify(results)
        except Exception as e:
            app.logger.exception(f"Universal Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/quantum", methods=["GET"])
    def screen_quantum():
        try:
            region = request.args.get("region", "us")
            time_frame = request.args.get("time_frame", "1d")
            app.logger.info(f"Quantum Screen request: region={region}, time_frame={time_frame}")
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

            app.logger.info(f"Quantum Screen completed. Results: {len(api_results)}")
            cache_screener_result(cache_key, api_results)
            return jsonify(api_results)
        except Exception as e:
            app.logger.exception(f"Quantum Screen Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/screen/check", methods=["GET"])
    def check_unified_stock():
        try:
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

            app.logger.info(f"Check Stock: {ticker_query}, Strategy: {strategy}")

            if not ticker_query:
                return jsonify({"error": "No ticker provided"}), 400

            ticker = screener.resolve_ticker(ticker_query)
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
                            app.logger.warning(f"Error accessing Close price: {inner}")
                            pass
                 except Exception as e:
                     app.logger.warning(f"Error fetching historical price for {ticker}: {e}")
                     pass

            results = []
            if strategy == "isa":
                results = screener.screen_trend_followers_isa(ticker_list=[ticker], check_mode=True, account_size=account_size)
            elif strategy == "turtle":
                results = screener.screen_turtle_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
            elif strategy == "darvas":
                results = screener.screen_darvas_box(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
            elif strategy == "ema" or strategy == "5/13":
                results = screener.screen_5_13_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
            elif strategy == "bull_put":
                results = screener.screen_bull_put_spreads(ticker_list=[ticker], check_mode=True)
            elif strategy == "hybrid":
                results = screener.screen_hybrid_strategy(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
            elif strategy == "mms":
                results = screener.screen_mms_ote_setups(ticker_list=[ticker], time_frame=time_frame, check_mode=True)
            elif strategy == "fourier":
                 results = screener.screen_fourier_cycles(ticker_list=[ticker], time_frame=time_frame)
            elif strategy == "master":
                 results = screener.screen_master_convergence(ticker_list=[ticker], check_mode=True)
            else:
                return jsonify({"error": f"Unknown strategy: {strategy}"}), 400

            if not results:
                 app.logger.info(f"No results for {ticker} in strategy {strategy}")
                 return jsonify({"error": f"No data returned for {ticker} with strategy {strategy}."}), 404

            result = results[0]

            if entry_price and result.get('price'):
                curr = result['price']
                result['pnl_value'] = curr - entry_price
                result['pnl_pct'] = ((curr - entry_price) / entry_price) * 100
                result['user_entry_price'] = entry_price

                signal = str(result.get('signal', 'WAIT')).upper()
                verdict = str(result.get('verdict', '')).upper()
                
                if strategy == "isa":
                    stop_exit = result.get('trailing_exit_20d', 0)
                    if curr <= stop_exit:
                         result['user_verdict'] = "🛑 EXIT (Stop Hit - Below 20d Low)"
                    elif "SELL" in signal or "AVOID" in signal:
                         result['user_verdict'] = "🛑 EXIT (Trend Reversed)"
                    else:
                         result['user_verdict'] = "✅ HOLD (Trend Valid)"
                
                elif strategy == "turtle":
                    trailing_exit = result.get('trailing_exit_10d', 0)
                    sl = result.get('stop_loss', 0)

                    if trailing_exit > 0 and curr < trailing_exit:
                        result['user_verdict'] = "🛑 EXIT (Below 10-Day Low)"
                    elif sl > 0 and curr < sl:
                         result['user_verdict'] = "🛑 EXIT (Stop Loss Hit)"
                    else:
                         result['user_verdict'] = "✅ HOLD (Trend Valid)"

                elif strategy == "ema":
                    if "SELL" in signal or "DUMP" in signal:
                         result['user_verdict'] = "🛑 EXIT (Bearish Cross)"
                    else:
                         result['user_verdict'] = "✅ HOLD (Momentum)"

                elif strategy == "fourier":
                    if "HIGH" in signal or "SELL" in signal:
                        result['user_verdict'] = "🛑 EXIT (Cycle Peak)"
                    elif "LOW" in signal or "BUY" in signal:
                         result['user_verdict'] = "✅ HOLD/ADD (Cycle Bottom)"
                    else:
                         result['user_verdict'] = "✅ HOLD (Mid-Cycle)"

                elif strategy == "master":
                    score = result.get('confluence_score', 0)
                    if score >= 2:
                         result['user_verdict'] = f"✅ STAY LONG ({score}/3 Bullish)"
                    else:
                         isa = result.get('isa_trend', 'NEUTRAL')
                         fourier = result.get('fourier', '')

                         if isa == "BEARISH" and "TOP" in str(fourier).upper():
                              result['user_verdict'] = "🛑 URGENT EXIT (Trend & Cycle Bearish)"
                         elif score == 1:
                              result['user_verdict'] = "⚠️ CAUTION (Only 1/3 Bullish)"
                         else:
                              result['user_verdict'] = "🛑 EXIT (No Confluence)"

                if 'user_verdict' not in result:
                    if "BUY" in signal or "GREEN" in signal or "BREAKOUT" in signal or "LONG" in signal or "BUY" in verdict:
                         result['user_verdict'] = "✅ HOLD (Signal Active)"
                    elif "SELL" in signal or "SHORT" in signal or "DUMP" in signal or "SELL" in verdict:
                         result['user_verdict'] = "🛑 EXIT (Signal Bearish)"
                    else:
                         result['user_verdict'] = "👀 WATCH (Neutral)"
            
            return jsonify(result)

        except Exception as e:
            app.logger.exception(f"Check Stock Error: {e}")
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
            app.logger.info(f"Journal entry added: {entry_id}")
            return jsonify({"success": True, "id": entry_id})
        except Exception as e:
            app.logger.error(f"Journal add error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/journal/delete/<entry_id>", methods=["DELETE"])
    def journal_delete_entry(entry_id):
        username = session.get('username')
        storage = get_storage_provider(app)
        storage.delete_journal_entry(username, entry_id)
        app.logger.info(f"Journal entry deleted: {entry_id}")
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
        journal_entries = []
        try:
            for trade in data:
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
                         except ValueError:
                             pass  # Ignore invalid date format

                if not entry_date:
                    entry_date = datetime.now().date().isoformat()

                journal_entry = {
                    "id": str(uuid.uuid4()),
                    "username": username,
                    "entry_date": entry_date,
                    "entry_time": entry_time,
                    "symbol": trade.get("symbol", ""),
                    "strategy": trade.get("strategy", ""),
                    "direction": "",
                    "entry_price": 0.0,
                    "exit_price": 0.0,
                    "qty": 1.0,
                    "pnl": float(trade.get("pnl", 0.0)),
                    "notes": f"Imported Analysis. Legs: {trade.get('legs_desc', '')}. Description: {trade.get('description', '')}",
                    "created_at": time.time()
                }
                journal_entries.append(journal_entry)

            count = storage.save_journal_entries(journal_entries)
            app.logger.info(f"Imported {count} trades for {username}")
            return jsonify({"success": True, "count": count})
        except Exception as e:
            app.logger.error(f"Import error: {e}")
            return jsonify({"error": str(e)}), 500

    # API Route for Analysis (Audit)
    @app.route("/analyze/portfolio", methods=["POST"])
    def analyze_portfolio_route():
        """
        Expects JSON: { "positions": [ {"ticker": "NVDA", "value": 5000}, ... ] }
        """
        try:
            data = request.json
            positions = data.get("positions", [])

            if not positions:
                return jsonify({"error": "No positions provided"}), 400

            report = portfolio_risk.analyze_portfolio_risk(positions)
            return jsonify(report)

        except Exception as e:
            app.logger.exception(f"Portfolio Analysis Error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/analyze", methods=["POST"])
    def analyze():
        app.logger.info("Portfolio Audit Request received")
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
                del res["excel_report"]

            res["token"] = token
            app.logger.info("Portfolio Audit completed successfully.")
            return jsonify(res)

        except Exception as exc:
            app.logger.exception(f"Audit failed: {exc}")
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
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode, ssl_context="adhoc")  # nosec
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)  # nosec
