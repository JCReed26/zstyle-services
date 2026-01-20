"""
ZStyle Database Engine Configuration

This module provides the SQLAlchemy async engine setup for the ZStyle system.
Requires PostgreSQL connection (Supabase). SQLite is not supported.

Supports graceful degradation when DATABASE_URL is not set or database is unavailable.

Usage:
    from database.engine import engine, AsyncSessionLocal, Base, get_db_session
"""
import os
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Get DATABASE_URL from environment - may be None for graceful degradation
DATABASE_URL = os.getenv("DATABASE_URL")

# Convert postgresql:// to postgresql+asyncpg:// for async support
parsed = None
if DATABASE_URL:
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Validate that we're using PostgreSQL (not SQLite)
    if not DATABASE_URL.startswith("postgresql"):
        logger.warning(
            f"Invalid DATABASE_URL: {DATABASE_URL}. "
            "Only PostgreSQL is supported. Database features disabled."
        )
        DATABASE_URL = None
    
    # Validate PostgreSQL connection format
    if DATABASE_URL:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
            if not parsed.hostname:
                logger.warning("DATABASE_URL missing hostname - database features disabled")
                DATABASE_URL = None
        except Exception as e:
            logger.warning(f"Invalid DATABASE_URL format: {e} - database features disabled")
            DATABASE_URL = None

if DATABASE_URL and parsed:
    logger.info(f"Database configured: PostgreSQL at {parsed.hostname}")
else:
    logger.warning("DATABASE_URL not set or invalid - database features will be disabled")

# =============================================================================
# ENGINE & SESSION SETUP
# =============================================================================

engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[sessionmaker] = None

if DATABASE_URL:
    # Connection pool configuration for PostgreSQL
    pool_config = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),  # 1 hour
        "pool_pre_ping": True,  # Verify connections before use
    }

    # Create async engine
    # echo=True in development for SQL query visibility
    echo_queries = os.getenv("ENV") == "development" and os.getenv("DB_ECHO", "false").lower() == "true"

    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=echo_queries,
            **pool_config
        )
        logger.info("Database engine created successfully")
        
        # Create async session factory
        AsyncSessionLocal = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        logger.warning("Database features will be disabled")
        engine = None
        AsyncSessionLocal = None

# Base class for all models
Base = declarative_base()

# Register engine with availability checker (will be None if unavailable)
try:
    from database.availability import set_database_engine
    set_database_engine(engine)
except ImportError:
    # Availability module not available yet, will be set later
    pass

# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_db_session():
    """
    FastAPI dependency for database sessions.
    
    Usage in FastAPI routes:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            ...
    
    Raises:
        RuntimeError: If database is not available
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database is not available")
    
    async with AsyncSessionLocal() as session:
        yield session
