from flask import Blueprint, request, jsonify, session, current_app, send_from_directory, g
import os
import threading
import json
from option_auditor.main_analyzer import refresh_dashboard_data
from webapp.storage import get_storage_provider as _get_storage_provider
from webapp.utils import send_email_notification
from webapp.validation import validate_schema
from webapp.schemas import FeedbackRequest

main_bp = Blueprint('main', __name__)

def get_db():
    if 'storage_provider' not in g:
        g.storage_provider = _get_storage_provider(current_app)
    return g.storage_provider

@main_bp.route("/feedback", methods=["POST"])
@validate_schema(FeedbackRequest, source='form')
def feedback():
    data: FeedbackRequest = g.validated_data
    username = session.get("username", "Anonymous")

    storage = get_db()
    try:
        storage.save_feedback(username, data.message, name=data.name, email=data.email)

        # --- NEW CODE: Send Email ---
        email_body = f"User: {username}\nName: {data.name or 'N/A'}\nEmail: {data.email or 'N/A'}\n\nMessage:\n{data.message}"
        # Run in background to avoid blocking response
        threading.Thread(target=send_email_notification, args=(f"New Feedback from {username}", email_body)).start()
        # ---------------------------

        current_app.logger.info(f"Feedback received from {username}")
        return jsonify({"success": True, "message": "Feedback submitted"})
    except Exception as e:
        current_app.logger.error(f"Feedback error: {e}")
        return jsonify({"error": "Failed to submit feedback"}), 500

@main_bp.route("/dashboard")
def dashboard():
    username = session.get('username')
    if not username:
            return jsonify({"error": "No session"}), 401

    current_app.logger.info(f"Dashboard access by {username}")
    storage = get_db()
    data_bytes = storage.get_portfolio(username)

    if not data_bytes:
        if os.environ.get("CI") == "true":
            # Seed mock data for CI E2E tests
            mock_data = {
                "net_liquidity": 100000.0,
                "buying_power": 50000.0,
                "positions": [{"symbol": "SPY", "qty": 100, "mark": 400.0, "value": 40000.0}],
                "greeks": {"delta": 50.0, "theta": -10.0, "gamma": 0.1, "vega": 100.0},
                "risk_map": {},
                "regime": "NEUTRAL"
            }
            storage.save_portfolio(username, json.dumps(mock_data).encode())
            data_bytes = storage.get_portfolio(username)
        else:
            return jsonify({"error": "No portfolio found"})

    try:
        saved_data = json.loads(data_bytes)
        updated_data = refresh_dashboard_data(saved_data)
        current_app.logger.info(f"Dashboard data refreshed for {username}")
        return jsonify(updated_data)
    except Exception as e:
        current_app.logger.error(f"Dashboard refresh error: {e}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/health")
def health():
    return "OK", 200

# Catch all route for React App
# Note: In blueprints, this might catch everything unless configured carefully.
# We usually want this last.
@main_bp.route("/", defaults={'path': ''})
@main_bp.route("/<path:path>")
def catch_all(path):
    # Allow requests to API routes or static files to pass through
    if path.startswith("api/") or path.startswith("static/") or path.startswith("download/"):
        return "Not Found", 404

    # Check if the requested file exists in the react build directory
    build_dir = os.path.join(current_app.static_folder, "react_build")
    if path != "" and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)

    # Otherwise serve index.html
    return send_from_directory(build_dir, "index.html")
