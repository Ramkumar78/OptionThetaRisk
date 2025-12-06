import sqlite3
import time
from .storage import StorageProvider

class LocalStorage(StorageProvider):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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
                    email TEXT PRIMARY KEY,
                    first_seen REAL,
                    last_seen REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    message TEXT,
                    created_at REAL
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

    def save_user(self, email: str) -> None:
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT email FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.execute("UPDATE users SET last_seen = ? WHERE email = ?", (now, email))
            else:
                conn.execute("INSERT INTO users (email, first_seen, last_seen) VALUES (?, ?, ?)", (email, now, now))

    def save_feedback(self, email: str, message: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO feedback (email, message, created_at) VALUES (?, ?, ?)",
                (email, message, time.time())
            )

    def close(self) -> None:
        pass
