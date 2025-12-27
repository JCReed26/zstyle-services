"""
ZStyle Database Engine Configuration

This module provides the SQLAlchemy async engine setup for the ZStyle system.
By default, it uses SQLite for development. Uncomment the Supabase section
for production deployment.

Usage:
    from database.core import engine, AsyncSessionLocal, Base, get_db_session

To reset the database during development:
    python reset_db.py
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# === DATABASE URL CONFIGURATION ===
# Prefer SQLite unless USE_POSTGRES=true. This avoids accidental remote DB attempts
# when DATABASE_URL is present in .env but Postgres is not reachable.
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = os.getenv("USE_POSTGRES", "").lower() in ("1", "true", "yes")

if USE_POSTGRES:
    if not DATABASE_URL:
        raise ValueError("USE_POSTGRES is true but DATABASE_URL is not set")
    # Fix for SQLAlchemy Async: 'postgresql://' -> 'postgresql+asyncpg://'
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    # Development: SQLite (default)
    # Use absolute path to match Docker mount point (/app/zstyle.db).
    # Override with SQLITE_DB_PATH if needed.
    sqlite_path = os.getenv("SQLITE_DB_PATH", "/app/zstyle.db")
    if os.path.isabs(sqlite_path):
        DATABASE_URL = f"sqlite+aiosqlite:///{sqlite_path}"
    else:
        DATABASE_URL = f"sqlite+aiosqlite:///{os.path.abspath(sqlite_path)}"

# =============================================================================
# ENGINE & SESSION SETUP
# =============================================================================

# Create async engine
# pool_pre_ping=True helps recover from lost connections (useful for Postgres)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries in console
    pool_pre_ping=True
)

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
