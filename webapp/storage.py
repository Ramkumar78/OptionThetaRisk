import os
import time
import uuid
import json
import logging
from abc import ABC, abstractmethod
import boto3
from sqlalchemy import create_engine, Column, String, LargeBinary, Float, Integer, Text, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

class Report(Base):
    __tablename__ = 'reports'
    token = Column(String, primary_key=True)
    filename = Column(String, primary_key=True)
    data = Column(LargeBinary)
    created_at = Column(Float, default=time.time)

class User(Base):
    __tablename__ = 'users'
    username = Column(String, primary_key=True)
    password_hash = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    location = Column(String)
    trading_experience = Column(String)
    created_at = Column(Float, default=time.time)
    last_login = Column(Float, default=time.time)

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    message = Column(Text)
    created_at = Column(Float, default=time.time)

class Portfolio(Base):
    __tablename__ = 'portfolios'
    username = Column(String, primary_key=True)
    data_json = Column(LargeBinary) # Storing JSON as bytes/blob
    updated_at = Column(Float, default=time.time)

class JournalEntry(Base):
    __tablename__ = 'journal_entries'
    id = Column(String, primary_key=True) # UUID
    username = Column(String)
    entry_date = Column(String)
    entry_time = Column(String)
    symbol = Column(String)
    strategy = Column(String)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    qty = Column(Float)
    pnl = Column(Float)
    sentiment = Column(String)
    notes = Column(Text)
    emotions = Column(Text)
    created_at = Column(Float, default=time.time)

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

    @abstractmethod
    def save_user(self, user_data: dict) -> None:
        pass

    @abstractmethod
    def get_user(self, username: str) -> dict:
        pass

    @abstractmethod
    def save_feedback(self, username: str, message: str, name: str = None, email: str = None) -> None:
        pass

    @abstractmethod
    def save_portfolio(self, username: str, data: bytes) -> None:
        pass

    @abstractmethod
    def get_portfolio(self, username: str) -> bytes:
        pass

    @abstractmethod
    def save_journal_entry(self, entry: dict) -> str:
        pass

    @abstractmethod
    def save_journal_entries(self, entries: list) -> int:
        pass

    @abstractmethod
    def get_journal_entries(self, username: str) -> list:
        pass

    @abstractmethod
    def delete_journal_entry(self, username: str, entry_id: str) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass

class DatabaseStorage(StorageProvider):
    # Class-level cache for engines to avoid re-creation (Singleton pattern for Engines)
    _engines = {}

    def __init__(self, db_url: str):
        self.db_url = db_url
        if db_url not in DatabaseStorage._engines:
            engine = create_engine(db_url)
            # Only perform migration checks on creation
            DatabaseStorage._ensure_schema_migrations(engine)
            DatabaseStorage._engines[db_url] = engine

        self.engine = DatabaseStorage._engines[db_url]
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.is_sqlite = db_url.startswith("sqlite")

    @staticmethod
    def _ensure_schema_migrations(engine):
        """
        Check for missing columns and migrate if necessary.
        Specifically for journal_entries: entry_date, entry_time
        """
        try:
            insp = inspect(engine)
            if insp.has_table('journal_entries'):
                columns = [c['name'] for c in insp.get_columns('journal_entries')]

                with engine.connect() as conn:
                    if 'entry_date' not in columns:
                        logger.info("Migrating: Adding entry_date to journal_entries")
                        conn.execute(text('ALTER TABLE journal_entries ADD COLUMN entry_date VARCHAR'))

                    if 'entry_time' not in columns:
                        logger.info("Migrating: Adding entry_time to journal_entries")
                        conn.execute(text('ALTER TABLE journal_entries ADD COLUMN entry_time VARCHAR'))

                    if 'sentiment' not in columns:
                        logger.info("Migrating: Adding sentiment to journal_entries")
                        conn.execute(text('ALTER TABLE journal_entries ADD COLUMN sentiment VARCHAR'))

                    if 'emotions' not in columns:
                        logger.info("Migrating: Adding emotions to journal_entries")
                        conn.execute(text('ALTER TABLE journal_entries ADD COLUMN emotions TEXT'))
                    conn.commit()
        except Exception as e:
            logger.error(f"Migration check failed: {e}")

    def save_report(self, token: str, filename: str, data: bytes) -> None:
        session = self.Session()
        try:
            report = Report(token=token, filename=filename, data=data)
            session.merge(report)
            session.commit()
        finally:
            session.close()

    def get_report(self, token: str, filename: str) -> bytes:
        session = self.Session()
        try:
            report = session.query(Report).filter_by(token=token, filename=filename).first()
            return report.data if report else None
        finally:
            session.close()

    def cleanup_old_reports(self, max_age_seconds: int) -> None:
        session = self.Session()
        try:
            cutoff = time.time() - max_age_seconds
            session.query(Report).filter(Report.created_at < cutoff).delete()
            session.commit()
            if self.is_sqlite:
                session.execute(text("VACUUM"))
        finally:
            session.close()

    def save_user(self, user_data: dict) -> None:
        session = self.Session()
        try:
            username = user_data.get('username')
            user = session.query(User).filter_by(username=username).first()
            if user:
                for k, v in user_data.items():
                    if hasattr(user, k):
                        setattr(user, k, v)
            else:
                user = User(**user_data)
            session.add(user)
            session.commit()
        finally:
            session.close()

    def get_user(self, username: str) -> dict:
        session = self.Session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user:
                return {c.name: getattr(user, c.name) for c in User.__table__.columns}
            return None
        finally:
            session.close()

    def save_feedback(self, username: str, message: str, name: str = None, email: str = None) -> None:
        session = self.Session()
        try:
            feedback = Feedback(username=username, message=message, name=name, email=email)
            session.add(feedback)
            session.commit()
        finally:
            session.close()

    def save_portfolio(self, username: str, data: bytes) -> None:
        session = self.Session()
        try:
            pf = Portfolio(username=username, data_json=data, updated_at=time.time())
            session.merge(pf)
            session.commit()
        finally:
            session.close()

    def get_portfolio(self, username: str) -> bytes:
        session = self.Session()
        try:
            pf = session.query(Portfolio).filter_by(username=username).first()
            return pf.data_json if pf else None
        finally:
            session.close()

    def save_journal_entry(self, entry: dict) -> str:
        session = self.Session()
        try:
            if 'id' not in entry or not entry['id']:
                entry['id'] = str(uuid.uuid4())

            # Sanitize inputs: keep only keys that exist in the model
            valid_keys = {c.name for c in JournalEntry.__table__.columns}
            sanitized_entry = {k: v for k, v in entry.items() if k in valid_keys}

            if 'emotions' in sanitized_entry and isinstance(sanitized_entry['emotions'], list):
                sanitized_entry['emotions'] = json.dumps(sanitized_entry['emotions'])

            db_entry = session.query(JournalEntry).filter_by(id=entry['id']).first()
            if db_entry:
                for k, v in sanitized_entry.items():
                     if hasattr(db_entry, k):
                        setattr(db_entry, k, v)
            else:
                db_entry = JournalEntry(**sanitized_entry)
                session.add(db_entry)

            session.commit()
            return entry['id']
        finally:
            session.close()

    def save_journal_entries(self, entries: list) -> int:
        """Batch save multiple journal entries in a single transaction."""
        if not entries:
            return 0

        session = self.Session()
        try:
            valid_keys = {c.name for c in JournalEntry.__table__.columns}
            count = 0

            # Prepare IDs if missing
            for entry in entries:
                if 'id' not in entry or not entry['id']:
                    entry['id'] = str(uuid.uuid4())

            # Identify existing entries to update vs insert
            ids = [e['id'] for e in entries]
            existing_records = session.query(JournalEntry).filter(JournalEntry.id.in_(ids)).all()
            existing_map = {r.id: r for r in existing_records}

            for entry in entries:
                sanitized_entry = {k: v for k, v in entry.items() if k in valid_keys}

                if 'emotions' in sanitized_entry and isinstance(sanitized_entry['emotions'], list):
                    sanitized_entry['emotions'] = json.dumps(sanitized_entry['emotions'])

                if entry['id'] in existing_map:
                    # Update
                    db_entry = existing_map[entry['id']]
                    for k, v in sanitized_entry.items():
                        if hasattr(db_entry, k):
                            setattr(db_entry, k, v)
                else:
                    # Insert
                    db_entry = JournalEntry(**sanitized_entry)
                    session.add(db_entry)
                count += 1

            session.commit()
            return count
        finally:
            session.close()

    def get_journal_entries(self, username: str) -> list:
        session = self.Session()
        try:
            entries = session.query(JournalEntry).filter_by(username=username).all()
            result = []
            columns = JournalEntry.__table__.columns
            for e in entries:
                row = {c.name: getattr(e, c.name) for c in columns}
                if row.get('emotions'):
                    try:
                        row['emotions'] = json.loads(row['emotions'])
                    except (json.JSONDecodeError, TypeError):
                         row['emotions'] = []
                else:
                     row['emotions'] = []
                result.append(row)
            return result
        finally:
            session.close()

    def delete_journal_entry(self, username: str, entry_id: str) -> None:
        session = self.Session()
        try:
            session.query(JournalEntry).filter_by(username=username, id=entry_id).delete()
            session.commit()
        finally:
            session.close()

    def close(self) -> None:
        # Do not dispose the engine here as it is cached at class level
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
        try:
            paginator = self.s3.get_paginator('list_objects_v2')
            cutoff = time.time() - max_age_seconds
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix='reports/'):
                if 'Contents' in page:
                    to_delete = []
                    for obj in page['Contents']:
                        if obj['LastModified'].timestamp() < cutoff:
                            to_delete.append({'Key': obj['Key']})
                    if to_delete:
                        for i in range(0, len(to_delete), 1000):
                            batch = to_delete[i:i+1000]
                            self.s3.delete_objects(
                                Bucket=self.bucket_name,
                                Delete={'Objects': batch}
                            )
        except Exception:
            pass

    def save_user(self, user_data: dict) -> None:
        username = user_data['username']
        key = f"users/{username}.json"
        try:
             import json
             self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(user_data).encode('utf-8')
            )
        except Exception:
            pass

    def get_user(self, username: str) -> dict:
        key = f"users/{username}.json"
        try:
            import json
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except Exception:
            return None

    def save_feedback(self, username: str, message: str, name: str = None, email: str = None) -> None:
        timestamp = int(time.time())
        key = f"feedback/{timestamp}_{username}.txt"
        content = f"User: {username}\nName: {name or 'N/A'}\nEmail: {email or 'N/A'}\n\nMessage:\n{message}"
        try:
             self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content.encode('utf-8')
            )
        except Exception:
            pass

    def save_portfolio(self, username: str, data: bytes) -> None:
        key = f"portfolios/{username}.json"
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data
            )
        except Exception:
            pass

    def get_portfolio(self, username: str) -> bytes:
        key = f"portfolios/{username}.json"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception:
            return None

    def _get_journal_s3_key(self, username: str) -> str:
        return f"journal/{username}.json"

    def save_journal_entry(self, entry: dict) -> str:
        import json
        username = entry['username']
        key = self._get_journal_s3_key(username)

        # Load existing
        entries = self.get_journal_entries(username)

        if 'id' not in entry or not entry['id']:
            entry['id'] = str(uuid.uuid4())

        # Update or Append
        found = False
        for i, e in enumerate(entries):
            if e['id'] == entry['id']:
                entries[i] = entry
                found = True
                break
        if not found:
            entries.append(entry)

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(entries).encode('utf-8')
            )
            return entry['id']
        except Exception:
            return None

    def save_journal_entries(self, new_entries_list: list) -> int:
        """Batch save for S3 (Naive implementation: Read-Modify-Write)."""
        if not new_entries_list:
            return 0

        import json
        # Assume all entries belong to same user for now, or group by user
        # In current app usage, bulk import is per user.
        username = new_entries_list[0]['username']
        key = self._get_journal_s3_key(username)

        # Load existing
        current_entries = self.get_journal_entries(username)
        current_map = {e['id']: i for i, e in enumerate(current_entries)}

        for entry in new_entries_list:
            if 'id' not in entry or not entry['id']:
                entry['id'] = str(uuid.uuid4())

            if entry['id'] in current_map:
                idx = current_map[entry['id']]
                current_entries[idx] = entry
            else:
                current_entries.append(entry)
                current_map[entry['id']] = len(current_entries) - 1

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(current_entries).encode('utf-8')
            )
            return len(new_entries_list)
        except Exception:
            return 0

    def get_journal_entries(self, username: str) -> list:
        import json
        key = self._get_journal_s3_key(username)
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except self.s3.exceptions.NoSuchKey:
            return []
        except Exception:
            return []

    def delete_journal_entry(self, username: str, entry_id: str) -> None:
        import json
        key = self._get_journal_s3_key(username)
        entries = self.get_journal_entries(username)

        new_entries = [e for e in entries if e['id'] != entry_id]

        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(new_entries).encode('utf-8')
            )
        except Exception:
            pass

    def close(self) -> None:
        pass

def get_storage_provider(app) -> StorageProvider:
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Fix for SQLAlchemy 1.4+ which deprecated 'postgres://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return DatabaseStorage(db_url)
    elif os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("S3_BUCKET_NAME"):
        return S3Storage(
            bucket_name=os.environ.get("S3_BUCKET_NAME"),
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
    else:
        # Fallback to local SQLite for simplicity if no other provider is configured
        db_path = os.path.join(app.instance_path, "reports.db")
        os.makedirs(app.instance_path, exist_ok=True)
        return DatabaseStorage(f"sqlite:///{db_path}")
