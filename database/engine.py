"""
ZStyle Database Engine Configuration

This module provides the SQLAlchemy async engine setup for the ZStyle system.
Requires PostgreSQL connection (Supabase). SQLite is not supported.

Usage:
    from database.engine import engine, AsyncSessionLocal, Base, get_db_session
"""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Get DATABASE_URL from environment - REQUIRED
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Set it to a PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/db). "
        "SQLite is not supported."
    )

# Convert postgresql:// to postgresql+asyncpg:// for async support
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Validate that we're using PostgreSQL (not SQLite)
if not DATABASE_URL.startswith("postgresql"):
    raise ValueError(
        f"Invalid DATABASE_URL: {DATABASE_URL}. "
        "Only PostgreSQL is supported. SQLite is not supported."
    )

# Validate PostgreSQL connection format
try:
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    if not parsed.hostname:
        raise ValueError("DATABASE_URL must include a hostname")
except Exception as e:
    raise ValueError(f"Invalid DATABASE_URL format: {e}") from e

logger.info(f"Database configured: PostgreSQL at {parsed.hostname}")

# =============================================================================
# ENGINE & SESSION SETUP
# =============================================================================

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
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise ValueError(
        f"Failed to connect to PostgreSQL database: {e}. "
        "Check your DATABASE_URL and ensure the database is accessible."
    ) from e

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all models
Base = declarative_base()


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
    """
    async with AsyncSessionLocal() as session:
        yield session
