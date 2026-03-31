import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from contextlib import contextmanager

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///output/app.db')

# 1. Connection Pooling & Production Settings
engine = create_engine(
    DATABASE_URL,
    pool_size=20 if not DATABASE_URL.startswith("sqlite") else 5,
    max_overflow=40 if not DATABASE_URL.startswith("sqlite") else 10,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Safe Transaction Handling (Atomic Operations)
@contextmanager
def get_db_session():
    """Context manager for atomic DB transactions with automatic rollback."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, index=True, nullable=True) # Added Index
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    users = relationship("User", back_populates="company")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='user')
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True) # Added Index
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    company = relationship("Company", back_populates="users")
    jobs = relationship("Job", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    org_name = Column(String, index=True, nullable=False) # Added Index
    org_url = Column(String, nullable=True)
    max_pages = Column(Integer, default=3)
    runs = Column(Integer, default=1)
    
    # Advanced State Machine: pending, running, retrying, failed, completed
    status = Column(String, default="pending", index=True) # Added Index
    progress = Column(JSON, default=dict)
    result_path = Column(String, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True) # Added Index
    company_id = Column(Integer, index=True, nullable=True) # Added Index
    industry_override = Column(String, nullable=True)
    
    # Cost tracking mechanism
    estimated_cost = Column(Integer, default=0) 
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True) # Added Index
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    user = relationship("User", back_populates="jobs")

def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
