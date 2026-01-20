"""
Database Availability Checker

Provides utilities to check if database is available and configured.
Used throughout the application for graceful degradation.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Global flag to track database availability
_db_available: Optional[bool] = None
_db_engine: Optional[AsyncEngine] = None


def set_database_engine(engine: Optional[AsyncEngine]) -> None:
    """
    Set the database engine instance.
    
    Called during application startup to register the engine.
    If None, database is considered unavailable.
    
    Args:
        engine: SQLAlchemy async engine or None
    """
    global _db_engine, _db_available
    _db_engine = engine
    _db_available = engine is not None
    if engine is None:
        logger.warning("Database engine not set - database features disabled")
    else:
        logger.info("Database engine registered successfully")


def is_database_available() -> bool:
    """
    Check if database is configured and available.
    
    Returns:
        True if database is available, False otherwise
    """
    global _db_available
    
    # Check if engine is set
    if _db_engine is None:
        return False
    
    return _db_available is not False


async def check_database_connection() -> bool:
    """
    Perform an actual database connection check.
    
    This is more expensive than is_database_available() but verifies
    the database is actually reachable.
    
    Returns:
        True if connection successful, False otherwise
    """
    if not is_database_available():
        return False
    
    try:
        async with _db_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.debug(f"Database connection check failed: {e}")
        return False


def require_database():
    """
    Raise an exception if database is not available.
    
    Use this in critical paths that absolutely require database.
    
    Raises:
        RuntimeError: If database is not available
    """
    if not is_database_available():
        raise RuntimeError(
            "Database is not available. "
            "This operation requires database access. "
            "Please check DATABASE_URL configuration."
        )
