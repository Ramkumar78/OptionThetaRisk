from __future__ import annotations

import os
import threading
import time
import logging
import sys
import uuid
from datetime import timedelta

from flask import Flask, jsonify, session, send_from_directory
from dotenv import load_dotenv

from webapp.storage import get_storage_provider as _get_storage_provider
from webapp.blueprints.screener_routes import screener_bp
from webapp.blueprints.journal_routes import journal_bp
from webapp.blueprints.analysis_routes import analysis_bp
from webapp.blueprints.main_routes import main_bp
from webapp.blueprints.safety_routes import safety_bp
from webapp.blueprints.strategy_routes import strategy_bp
from webapp.services.scheduler_service import start_scheduler

# Load environment variables from .env file
load_dotenv()

# Cleanup interval in seconds
CLEANUP_INTERVAL = 1200 # 20 minutes
# Max age of reports in seconds
MAX_REPORT_AGE = 1200 # 20 minutes

def cleanup_job(app):
    """Background thread to clean up old reports."""
    with app.app_context():
        # Here we don't have 'g', so we call factory directly.
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

    # Check for pytest environment to prevent background threads during tests
    # Checking sys.modules is more reliable during import time than env vars
    is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

    # Check if background tasks are disabled (e.g. for CI/E2E)
    disable_background = os.environ.get("DISABLE_BACKGROUND_TASKS", "false").lower() == "true"

    if not testing and not is_pytest and not disable_background and (not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"):
        t = threading.Thread(target=cleanup_job, args=(app,), daemon=True)
        t.start()
        # Start Headless Scanner
        start_scheduler(app)

    # Register Blueprints
    app.register_blueprint(screener_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(safety_bp)
    app.register_blueprint(strategy_bp)

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

    return app

app = create_app()

if __name__ == "__main__":
    enable_https = os.environ.get("ENABLE_HTTPS", "0") == "1"
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"

    if enable_https:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode, ssl_context="adhoc")  # nosec
    else:
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)  # nosec
