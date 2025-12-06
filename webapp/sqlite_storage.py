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
                # VACUUM cannot be run inside a transaction
                conn.commit()
                conn.execute("VACUUM")
        except Exception:
            pass

    def close(self) -> None:
        pass
