"""
Pytest Configuration and Fixtures

Provides shared test fixtures for:
- Test database setup/teardown
- Test client for API testing
- Mock Redis client
- Sample test data
"""

import pytest
import os
import sys
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from common.database import Base, get_db_session
from api.main import app


# Test Database Configuration
TEST_DATABASE_URL = "sqlite:///./test_fx_monitor.db"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()  # Close all connections before deleting
    # Clean up test database file
    try:
        if os.path.exists("./test_fx_monitor.db"):
            os.remove("./test_fx_monitor.db")
    except PermissionError:
        pass  # File still in use, will be cleaned up later


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client(test_engine):
    """Create a test client with test database."""
    def override_get_db():
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_rates():
    """Sample FX rate data for testing."""
    return {
        "USD/EUR": 0.85,
        "USD/GBP": 0.73,
        "USD/JPY": 149.50,
        "USD/CAD": 1.35,
        "USD/AUD": 1.52,
        "USD/CHF": 0.88,
        "USD/CNY": 7.24,
        "USD/INR": 83.12
    }


@pytest.fixture
def sample_alert():
    """Sample alert data for testing."""
    return {
        "pair": "USD/EUR",
        "condition": "above",
        "threshold": 0.90
    }


@pytest.fixture
def mock_redis_data():
    """Mock Redis data for testing."""
    return {
        "fx:USD/EUR": "0.85",
        "fx:USD/GBP": "0.73",
        "fx:USD/JPY": "149.50"
    }
