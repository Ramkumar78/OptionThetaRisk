import os
import time
import uuid
from abc import ABC, abstractmethod
from flask import current_app
import boto3
from sqlalchemy import create_engine, text, Column, String, LargeBinary, Float, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base

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
    notes = Column(Text)
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
    def save_feedback(self, username: str, message: str) -> None:
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
    def get_journal_entries(self, username: str) -> list:
        pass

    @abstractmethod
    def delete_journal_entry(self, username: str, entry_id: str) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass

    def initialize(self) -> None:
        """Perform one-time initialization (e.g. creating tables)."""
        pass

class PostgresStorage(StorageProvider):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def initialize(self) -> None:
        """Create tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            # Log error but don't crash app if DB is temporarily down
            # However, if tables don't exist, app will fail later.
            print(f"Warning: Failed to initialize database schema: {e}")

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

    def save_feedback(self, username: str, message: str) -> None:
        session = self.Session()
        try:
            feedback = Feedback(username=username, message=message)
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

            db_entry = session.query(JournalEntry).filter_by(id=entry['id']).first()
            if db_entry:
                for k, v in entry.items():
                     if hasattr(db_entry, k):
                        setattr(db_entry, k, v)
            else:
                db_entry = JournalEntry(**entry)
                session.add(db_entry)

            session.commit()
            return entry['id']
        finally:
            session.close()

    def get_journal_entries(self, username: str) -> list:
        session = self.Session()
        try:
            entries = session.query(JournalEntry).filter_by(username=username).all()
            return [{c.name: getattr(e, c.name) for c in JournalEntry.__table__.columns} for e in entries]
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
        self.engine.dispose()

def get_storage_provider(app) -> StorageProvider:
    if os.environ.get("DATABASE_URL"):
        return PostgresStorage(os.environ.get("DATABASE_URL"))
    else:
        # Fallback to local SQLite for simplicity if no other provider is configured
        print("Warning: DATABASE_URL not set. Using temporary SQLite storage. Data will be lost on restart.")
        db_path = os.path.join(app.instance_path, "reports.db")
        from .sqlite_storage import LocalStorage
        return LocalStorage(db_path)
