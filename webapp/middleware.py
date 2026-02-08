from __future__ import annotations

import time
import os
import uuid
import logging
import psutil
from flask import Flask, request, g, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
from sqlalchemy import text

# Try importing storage. If it fails (e.g. during minimal testing), handle gracefully.
try:
    from webapp.storage import get_storage_provider, DatabaseStorage, S3Storage
except ImportError:
    get_storage_provider = None
    DatabaseStorage = None
    S3Storage = None

logger = logging.getLogger(__name__)

# Initialize extensions globally
# Storage defaults to memory if not specified.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

compress = Compress()

def setup_middleware(app: Flask):
    """
    Sets up all middleware including:
    1. Request ID tracking
    2. Gzip Compression
    3. Rate Limiting
    4. Health Check Endpoint
    """

    # 1. Request ID Middleware
    @app.before_request
    def add_request_id():
        # Check if X-Request-ID header exists, otherwise generate one
        req_id = request.headers.get('X-Request-ID')
        if not req_id:
            req_id = str(uuid.uuid4())
        g.request_id = req_id

    @app.after_request
    def append_request_id(response: Response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response

    # 2. Initialize Extensions with App
    limiter.init_app(app)
    compress.init_app(app)

    # 3. Custom Error Handler for Rate Limit
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "error": "ratelimit_exceeded",
            "message": str(e.description) if hasattr(e, 'description') else "Too many requests"
        }), 429

    # 4. Health Check Endpoint
    @app.route("/health")
    @limiter.exempt
    def health_check():
        status_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "webapp",
            "memory": {},
            "storage": "unknown"
        }

        # Check Memory
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            status_data["memory"] = {
                "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
                "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except Exception as e:
            status_data["memory"] = {"error": str(e)}

        # Check Storage
        try:
            if get_storage_provider:
                storage = get_storage_provider(app)

                if DatabaseStorage and isinstance(storage, DatabaseStorage):
                    # Check DB connection
                    with storage.engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    status_data["storage"] = "connected (database)"
                elif S3Storage and isinstance(storage, S3Storage):
                    if storage.bucket_name:
                        status_data["storage"] = f"configured (s3: {storage.bucket_name})"
                    else:
                        status_data["storage"] = "misconfigured (s3)"
                else:
                    status_data["storage"] = "connected (unknown/local)"
            else:
                status_data["storage"] = "storage_module_missing"

        except Exception as e:
            status_data["status"] = "unhealthy"
            status_data["storage_error"] = str(e)
            return jsonify(status_data), 503

        return jsonify(status_data)

    return app
