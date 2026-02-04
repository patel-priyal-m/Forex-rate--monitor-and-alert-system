"""
Common utilities package for shared infrastructure.

This package contains:
- database.py: SQLAlchemy models and database session management
- redis_client.py: Redis connection and caching utilities

Used by:
- consumer/rate_processor.py (Phase 2)
- consumer/alert_engine.py (Phase 3)
- api/main.py (Phase 3)
"""

__version__ = "0.2.0"
