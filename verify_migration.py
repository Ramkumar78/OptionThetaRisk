import os
import sqlite3
import uuid
import time
from webapp.storage import DatabaseStorage, JournalEntry

DB_PATH = "test_migration.db"
DB_URL = f"sqlite:///{DB_PATH}"

def create_old_schema():
    """Create a database with the OLD schema (missing columns)."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create table WITHOUT entry_date, entry_time
    c.execute('''
        CREATE TABLE journal_entries (
            id VARCHAR PRIMARY KEY,
            username VARCHAR,
            symbol VARCHAR,
            strategy VARCHAR,
            direction VARCHAR,
            entry_price FLOAT,
            exit_price FLOAT,
            qty FLOAT,
            pnl FLOAT,
            sentiment VARCHAR,
            notes TEXT,
            created_at FLOAT
        )
    ''')
    conn.commit()
    conn.close()
    print("Created old schema DB.")

def verify_migration():
    print("Initializing DatabaseStorage (should trigger migration)...")
    storage = DatabaseStorage(DB_URL)

    # Verify columns exist using raw SQLite inspection
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(journal_entries)")
    columns = [row[1] for row in c.fetchall()]
    conn.close()

    print(f"Columns after migration: {columns}")

    if "entry_date" in columns and "entry_time" in columns:
        print("SUCCESS: Columns were added.")
    else:
        print("FAILURE: Columns missing.")
        exit(1)

    # Test adding an entry with new fields
    entry = {
        "id": str(uuid.uuid4()),
        "username": "test_user",
        "entry_date": "2023-01-01",
        "entry_time": "12:00",
        "symbol": "TEST",
        "strategy": "Long",
        "pnl": 100.0,
        "sentiment": "Bullish",
        "notes": "Migration test",
        "extra_junk_field": "Should be ignored" # Test sanitization
    }

    print("Attempting to save entry with new fields and extra junk...")
    try:
        storage.save_journal_entry(entry)
        print("Entry saved successfully.")
    except Exception as e:
        print(f"FAILURE: save_journal_entry raised exception: {e}")
        exit(1)

    # Verify data retention
    saved = storage.get_journal_entries("test_user")[0]
    if saved['entry_date'] == "2023-01-01" and saved['entry_time'] == "12:00":
        print("SUCCESS: New fields persisted correctly.")
    else:
        print(f"FAILURE: Data mismatch. Saved: {saved}")
        exit(1)

    storage.close()

if __name__ == "__main__":
    create_old_schema()
    verify_migration()
    # Cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
