import os
import io
import time
import sqlite3
import boto3
from abc import ABC, abstractmethod
from flask import current_app

class StorageProvider(ABC):
    @abstractmethod
    def save_report(self, token: str, filename: str, data: bytes) -> None:
        pass

    @abstractmethod
    def get_report(self, token: str, filename: str) -> bytes:
        pass

    @abstractmethod
    def cleanup_old_reports(self, max_age_seconds: int) -> None:
        pass

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
        except Exception:
            pass

class S3Storage(StorageProvider):
    def __init__(self, bucket_name: str, region_name: str = None):
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3', region_name=region_name)

    def save_report(self, token: str, filename: str, data: bytes) -> None:
        key = f"reports/{token}/{filename}"
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data
        )

    def get_report(self, token: str, filename: str) -> bytes:
        key = f"reports/{token}/{filename}"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception:
            return None

    def cleanup_old_reports(self, max_age_seconds: int) -> None:
        # S3 cleanup is expensive to list all objects.
        # Ideally, we should rely on S3 Lifecycle Policies.
        # But for completeness, we implement a simple list-and-delete.
        # Note: This might be slow if there are many objects.
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            cutoff = time.time() - max_age_seconds

            # We iterate prefix "reports/"
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix='reports/'):
                if 'Contents' in page:
                    to_delete = []
                    for obj in page['Contents']:
                        # LastModified is a datetime object with timezone info
                        if obj['LastModified'].timestamp() < cutoff:
                            to_delete.append({'Key': obj['Key']})

                    if to_delete:
                        # Batch delete (max 1000 keys)
                        for i in range(0, len(to_delete), 1000):
                            batch = to_delete[i:i+1000]
                            self.s3.delete_objects(
                                Bucket=self.bucket_name,
                                Delete={'Objects': batch}
                            )
        except Exception:
            pass

def get_storage_provider(app) -> StorageProvider:
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("S3_BUCKET_NAME"):
        return S3Storage(
            bucket_name=os.environ.get("S3_BUCKET_NAME"),
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
    else:
        db_path = os.path.join(app.instance_path, "reports.db")
        return LocalStorage(db_path)
