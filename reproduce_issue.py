import sqlite3
import os
from sqlalchemy import create_engine, inspect, text
from webapp.storage import DatabaseStorage

DB_PATH = "reproduce.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Create a legacy database without 'sentiment'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE journal_entries (
        id VARCHAR PRIMARY KEY,
        username VARCHAR,
        entry_date VARCHAR,
        entry_time VARCHAR,
        symbol VARCHAR,
        strategy VARCHAR,
        direction VARCHAR,
        entry_price FLOAT,
        exit_price FLOAT,
        qty FLOAT,
        pnl FLOAT,
        notes TEXT,
        created_at FLOAT
    )
''')
conn.commit()
conn.close()

print("Created legacy database.")

# Now initialize DatabaseStorage, which should trigger migration
storage = DatabaseStorage(f"sqlite:///{DB_PATH}")

# Inspect columns
insp = inspect(storage.engine)
columns = [c['name'] for c in insp.get_columns('journal_entries')]

if 'sentiment' in columns:
    print("SUCCESS: 'sentiment' column found.")
else:
    print("FAILURE: 'sentiment' column missing.")

# Cleanup
storage.close()
# os.remove(DB_PATH)
