"""
Database models and session management using SQLAlchemy.

This module provides:
- SQLAlchemy ORM models for fx_rates, user_alerts, alert_history
- Database session factory
- Database initialization function
"""

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship


# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://fxuser:fxpass@localhost:5432/fxdb')

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # Connection pool size
    max_overflow=20,       # Max connections beyond pool_size
    pool_pre_ping=True,    # Verify connections before using
    echo=False             # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class FXRate(Base):
    """
    Historical foreign exchange rate records.
    
    Stores all rate updates received from Kafka for time-series analysis.
    """
    __tablename__ = 'fx_rates'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    pair = Column(String(10), nullable=False, index=True)  # e.g., "USD/EUR"
    rate = Column(Float, nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_fx_rates_pair_timestamp', 'pair', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<FXRate(pair='{self.pair}', rate={self.rate}, timestamp={self.timestamp})>"


class UserAlert(Base):
    """
    User-configured rate alerts.
    
    Defines thresholds that trigger notifications when rates cross specific values.
    """
    __tablename__ = 'user_alerts'
    
    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(10), nullable=False, index=True)  # e.g., "USD/EUR"
    condition = Column(String(10), nullable=False)  # "above" or "below"
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to alert history
    triggered_alerts = relationship("AlertHistory", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserAlert(pair='{self.pair}', {self.condition} {self.threshold}, active={self.active})>"


class AlertHistory(Base):
    """
    History of triggered alerts.
    
    Records when alerts were triggered for audit and notification purposes.
    """
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey('user_alerts.id'), nullable=False, index=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    pair = Column(String(10), nullable=False)
    rate = Column(Float, nullable=False)
    message = Column(String(255), nullable=False)
    
    # Relationship to parent alert
    alert = relationship("UserAlert", back_populates="triggered_alerts")
    
    def __repr__(self):
        return f"<AlertHistory(pair='{self.pair}', rate={self.rate}, triggered_at={self.triggered_at})>"


def init_db():
    """
    Initialize database by creating all tables.
    
    Should be called once during application startup.
    Safe to call multiple times (creates only if not exists).
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_session() -> Generator[Session, None, None]:
    """
    Dependency injection function for database sessions.
    
    Yields:
        Session: SQLAlchemy database session
        
    Usage:
        with get_session() as session:
            rates = session.query(FXRate).all()
    
    Or with FastAPI:
        @app.get("/rates")
        def get_rates(db: Session = Depends(get_session)):
            return db.query(FXRate).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a database session directly (not as generator).
    
    Returns:
        Session: SQLAlchemy database session
        
    Note: Caller is responsible for closing the session!
    
    Usage:
        session = get_db_session()
        try:
            rates = session.query(FXRate).all()
        finally:
            session.close()
    """
    return SessionLocal()


if __name__ == '__main__':
    # Test database connection and create tables
    print(f"Connecting to: {DATABASE_URL}")
    init_db()
    
    # Test session
    session = get_db_session()
    try:
        # Query to test connection
        count = session.query(FXRate).count()
        print(f"✅ Database connection successful. FXRate records: {count}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    finally:
        session.close()
