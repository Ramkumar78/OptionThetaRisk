from flask import Blueprint, request, jsonify, session, current_app, g
import uuid
import time
from datetime import datetime
from option_auditor import journal_analyzer
from webapp.storage import get_storage_provider as _get_storage_provider
from webapp.validation import validate_schema
from webapp.schemas import JournalEntryRequest, JournalImportRequest

journal_bp = Blueprint('journal', __name__)

def get_db():
    if 'storage_provider' not in g:
        g.storage_provider = _get_storage_provider(current_app)
    return g.storage_provider

@journal_bp.route("/journal", methods=["GET"])
def journal_get_entries():
    username = session.get('username')
    storage = get_db()
    entries = storage.get_journal_entries(username)
    return jsonify(entries)

@journal_bp.route("/journal/add", methods=["POST"])
@validate_schema(JournalEntryRequest)
def journal_add_entry():
    username = session.get('username')
    data = g.validated_data.model_dump()

    data['username'] = username
    data['created_at'] = time.time()

    storage = get_db()
    try:
        entry_id = storage.save_journal_entry(data)
        current_app.logger.info(f"Journal entry added: {entry_id}")
        return jsonify({"success": True, "id": entry_id})
    except Exception as e:
        current_app.logger.error(f"Journal add error: {e}")
        return jsonify({"error": str(e)}), 500

@journal_bp.route("/journal/delete/<entry_id>", methods=["DELETE"])
def journal_delete_entry(entry_id):
    username = session.get('username')
    storage = get_db()
    storage.delete_journal_entry(username, entry_id)
    current_app.logger.info(f"Journal entry deleted: {entry_id}")
    return jsonify({"success": True})

@journal_bp.route("/journal/analyze", methods=["POST"])
def journal_analyze_batch():
    username = session.get('username')
    storage = get_db()
    entries = storage.get_journal_entries(username)
    result = journal_analyzer.analyze_journal(entries)
    return jsonify(result)

@journal_bp.route("/journal/import", methods=["POST"])
@validate_schema(JournalImportRequest)
def journal_import_trades():
    username = session.get('username')
    data = g.validated_data.root

    storage = get_db()
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
        current_app.logger.info(f"Imported {count} trades for {username}")
        return jsonify({"success": True, "count": count})
    except Exception as e:
        current_app.logger.error(f"Import error: {e}")
        return jsonify({"error": str(e)}), 500
