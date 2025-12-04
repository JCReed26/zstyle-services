import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database URL for Supabase (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to sqlite for local dev if no env var
    DATABASE_URL = "sqlite+aiosqlite:///zstyle.db"
    print("WARNING: DATABASE_URL not set. Using local SQLite: zstyle.db")

# Fix for SQLAlchemy Async: 'postgresql://' -> 'postgresql+asyncpg://'
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
# pool_pre_ping=True helps recover from lost connections
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
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

# Dependency to get DB session
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
