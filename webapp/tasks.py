import os
import json
import io
import time
from datetime import datetime
from celery import Celery
from webapp.storage import get_storage_provider, SaaSStorage, PostgresStorage
from option_auditor import analyze_csv

# Configure Celery
# If CELERY_BROKER_URL is not set, we default to something that won't work in prod,
# but the app.py handles the fallback.
def make_celery(app_name=__name__):
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    celery = Celery(app_name, broker=broker_url, backend=result_backend)

    # Optional config
    celery.conf.update(
        result_expires=3600,
    )
    return celery

celery_app = make_celery()

@celery_app.task(bind=True)
def analyze_csv_task(self, upload_key, options):
    """
    Celery task to analyze a CSV file.

    Args:
        upload_key: The key to retrieve the uploaded CSV from storage.
        options: A dictionary containing analysis options (username, broker, fees, etc.)
    """

    # Re-initialize storage within the task (different process)
    # We need to manually construct the storage provider as we don't have the Flask app context
    # exactly the same way, but we can rely on env vars.

    # We only support this task if running in SaaS mode (Postgres + S3) usually.
    # But let's reuse the get_storage_provider logic but we might need a dummy app object
    # or just instantiate SaaSStorage directly if env vars are present.

    db_url = os.environ.get("DATABASE_URL")
    bucket_name = os.environ.get("S3_BUCKET_NAME")

    storage = None
    if db_url and bucket_name:
         storage = SaaSStorage(db_url, bucket_name, os.environ.get("AWS_REGION", "us-east-1"))
    elif db_url:
         # Fallback to PostgresStorage (no S3)
         storage = PostgresStorage(db_url)
    else:
        # Fallback or error?
        # If we are running this task, we assume SaaS environment.
        return {"error": "Storage configuration missing in worker."}

    # 1. Retrieve the CSV file
    csv_bytes = storage.get_upload(upload_key)
    if not csv_bytes:
        return {"error": "Upload file not found."}

    csv_path = io.StringIO(csv_bytes.decode('utf-8'))

    # 2. Extract options
    broker = options.get("broker", "auto")
    account_size_start = options.get("account_size_start")
    net_liquidity_now = options.get("net_liquidity_now")
    buying_power_available_now = options.get("buying_power_available_now")
    style = options.get("style", "income")
    global_fees = options.get("global_fees")
    start_date = options.get("start_date")
    end_date = options.get("end_date")
    manual_data = options.get("manual_data")
    token = options.get("token")
    username = options.get("username")

    # 3. Update task state
    self.update_state(state='PROCESSING', meta={'status': 'Analyzing data...'})

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
            global_fees=global_fees,
            style=style
        )

        if "error" in res:
            return {"error": res["error"]}

        # 4. Save Excel Report
        if res.get("excel_report"):
            storage.save_report(token, "report.xlsx", res["excel_report"].getvalue())

        # 5. Save Portfolio (JSON)
        if username:
            to_save = res.copy()
            if "excel_report" in to_save:
                del to_save["excel_report"]

            to_save["saved_at"] = datetime.now().isoformat()
            to_save["token"] = token
            to_save["style"] = style

            storage.save_portfolio(username, json.dumps(to_save).encode('utf-8'))

        # Clean up the return value (don't return BytesIO)
        if "excel_report" in res:
            del res["excel_report"]

        # Add token to result so frontend knows where to fetch things
        res["token"] = token

        return res

    except Exception as exc:
        return {"error": str(exc)}
    finally:
        storage.close()
