"""
ZStyle Database Engine Configuration

This module provides the SQLAlchemy async engine setup for the ZStyle system.
By default, it uses SQLite for development. Uncomment the Supabase section
for production deployment.

Usage:
    from database.engine import engine, AsyncSessionLocal, Base, get_db_session

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

# === PRODUCTION: Uncomment for Supabase/PostgreSQL ===
# DATABASE_URL = os.getenv("DATABASE_URL")
# if not DATABASE_URL:
#     raise ValueError("DATABASE_URL environment variable is required for production")
# # Fix for SQLAlchemy Async: 'postgresql://' -> 'postgresql+asyncpg://'
# if DATABASE_URL.startswith("postgresql://"):
#     DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# === DEVELOPMENT: SQLite (default) ===
# Simple file-based database, easy to reset during development
DATABASE_URL = "sqlite+aiosqlite:///zstyle.db"

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
