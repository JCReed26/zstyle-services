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
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()


def _get_secret_from_gcp(secret_name: str) -> Optional[str]:
    """
    Retrieve secret from Google Secret Manager.
    Only used in production (Cloud Run).
    """
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            return None
        
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception:
        # Not in GCP or secret not available
        return None

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# === DATABASE URL CONFIGURATION ===
# Prefer SQLite unless USE_POSTGRES=true. This avoids accidental remote DB attempts
# when DATABASE_URL is present in .env but Postgres is not reachable.
DATABASE_URL = os.getenv("DATABASE_URL") or _get_secret_from_gcp("DATABASE_URL")
USE_POSTGRES = os.getenv("USE_POSTGRES", "").lower() in ("1", "true", "yes")

if USE_POSTGRES:
    if not DATABASE_URL:
        raise ValueError("USE_POSTGRES is true but DATABASE_URL is not set")
    
    # Cloud SQL Unix socket connection (production)
    # Format: postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Ensure asyncpg driver is used
    if "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    # Development: SQLite (default)
    # Use absolute path to match Docker mount point (/app/zstyle.db).
    # Override with SQLITE_DB_PATH if needed.
    sqlite_path = os.getenv("SQLITE_DB_PATH", "/app/data/zstyle.db")
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
    pool_pre_ping=True,
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Max overflow connections
    pool_recycle=3600,  # Recycle connections after 1 hour
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
