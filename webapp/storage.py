import os
import time
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
    email = Column(String, primary_key=True)
    first_seen = Column(Float, default=time.time)
    last_seen = Column(Float, default=time.time)

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String)
    message = Column(Text)
    created_at = Column(Float, default=time.time)

class Portfolio(Base):
    __tablename__ = 'portfolios'
    email = Column(String, primary_key=True)
    data_json = Column(LargeBinary) # Storing JSON as bytes/blob
    updated_at = Column(Float, default=time.time)

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
    def save_user(self, email: str) -> None:
        pass

    @abstractmethod
    def save_feedback(self, email: str, message: str) -> None:
        pass

    @abstractmethod
    def save_portfolio(self, email: str, data: bytes) -> None:
        pass

    @abstractmethod
    def get_portfolio(self, email: str) -> bytes:
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass

class PostgresStorage(StorageProvider):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

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

    def save_user(self, email: str) -> None:
        session = self.Session()
        try:
            user = session.query(User).filter_by(email=email).first()
            if user:
                user.last_seen = time.time()
            else:
                user = User(email=email)
            session.add(user)
            session.commit()
        finally:
            session.close()

    def save_feedback(self, email: str, message: str) -> None:
        session = self.Session()
        try:
            feedback = Feedback(email=email, message=message)
            session.add(feedback)
            session.commit()
        finally:
            session.close()

    def save_portfolio(self, email: str, data: bytes) -> None:
        session = self.Session()
        try:
            pf = Portfolio(email=email, data_json=data, updated_at=time.time())
            session.merge(pf)
            session.commit()
        finally:
            session.close()

    def get_portfolio(self, email: str) -> bytes:
        session = self.Session()
        try:
            pf = session.query(Portfolio).filter_by(email=email).first()
            return pf.data_json if pf else None
        finally:
            session.close()

    def close(self) -> None:
        self.engine.dispose()

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

    def save_user(self, email: str) -> None:
        key = f"users/{email}"
        try:
             self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=str(time.time()).encode('utf-8')
            )
        except Exception:
            pass

    def save_feedback(self, email: str, message: str) -> None:
        timestamp = int(time.time())
        key = f"feedback/{timestamp}_{email}.txt"
        try:
             self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=message.encode('utf-8')
            )
        except Exception:
            pass

    def save_portfolio(self, email: str, data: bytes) -> None:
        key = f"portfolios/{email}.json"
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data
            )
        except Exception:
            pass

    def get_portfolio(self, email: str) -> bytes:
        key = f"portfolios/{email}.json"
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self.s3.exceptions.NoSuchKey:
            return None
        except Exception:
            return None

    def close(self) -> None:
        pass

def get_storage_provider(app) -> StorageProvider:
    if os.environ.get("DATABASE_URL"):
        return PostgresStorage(os.environ.get("DATABASE_URL"))
    elif os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("S3_BUCKET_NAME"):
        return S3Storage(
            bucket_name=os.environ.get("S3_BUCKET_NAME"),
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
    else:
        # Fallback to local SQLite for simplicity if no other provider is configured
        db_path = os.path.join(app.instance_path, "reports.db")
        from .sqlite_storage import LocalStorage
        return LocalStorage(db_path)
