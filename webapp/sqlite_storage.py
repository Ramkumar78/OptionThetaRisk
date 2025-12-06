import sqlite3
import time
from .storage import StorageProvider

class LocalStorage(StorageProvider):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Migration: Drop old tables if schema changed significantly (Sandbox only)
            # In a real app, we'd use Alembic or similar.
            # Here, we need to add username, password, etc.
            # We'll just create if not exists, but the user table needs to be different.
            # Let's drop users table to be safe since we are changing PK and fields.
            # Check if columns exist? No, simplest is drop.
            try:
                # Check if old table exists
                cursor = conn.execute("PRAGMA table_info(users)")
                cols = [row[1] for row in cursor.fetchall()]
                if 'email' in cols and 'username' not in cols:
                    conn.execute("DROP TABLE users")
                    conn.execute("DROP TABLE portfolios") # Needs to be re-keyed
                    conn.execute("DROP TABLE feedback")
            except Exception:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    token TEXT,
                    filename TEXT,
                    data BLOB,
                    created_at REAL,
                    PRIMARY KEY (token, filename)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    location TEXT,
                    trading_experience TEXT,
                    created_at REAL,
                    last_login REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    message TEXT,
                    created_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    username TEXT PRIMARY KEY,
                    data_json BLOB,
                    updated_at REAL
                )
            """)

    def save_report(self, token: str, filename: str, data: bytes) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO reports (token, filename, data, created_at) VALUES (?, ?, ?, ?)",
                (token, filename, data, time.time())
            )

    def get_report(self, token: str, filename: str) -> bytes:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM reports WHERE token = ? AND filename = ?", (token, filename)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def cleanup_old_reports(self, max_age_seconds: int) -> None:
        cutoff = time.time() - max_age_seconds
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM reports WHERE created_at < ?", (cutoff,))
        except Exception:
            pass

    def save_user(self, user_data: dict) -> None:
        username = user_data['username']
        with sqlite3.connect(self.db_path) as conn:
            # Check if user exists
            cursor = conn.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                # Update
                fields = []
                values = []
                for k, v in user_data.items():
                    if k != 'username':
                        fields.append(f"{k} = ?")
                        values.append(v)
                if fields:
                    values.append(username)
                    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE username = ?", values)
            else:
                # Insert
                keys = list(user_data.keys())
                values = list(user_data.values())
                placeholders = ",".join(["?"] * len(keys))
                conn.execute(f"INSERT INTO users ({', '.join(keys)}) VALUES ({placeholders})", values)

    def get_user(self, username: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def save_feedback(self, username: str, message: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO feedback (username, message, created_at) VALUES (?, ?, ?)",
                (username, message, time.time())
            )

    def save_portfolio(self, username: str, data: bytes) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO portfolios (username, data_json, updated_at) VALUES (?, ?, ?)",
                (username, data, time.time())
            )

    def get_portfolio(self, username: str) -> bytes:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data_json FROM portfolios WHERE username = ?", (username,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def close(self) -> None:
        pass
