"""
SQLite Database Connection
Connection and interface for interacting with the local SQLite Database.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database URL for SQLite
# Use a local file 'zstyle.db'
DATABASE_URL = "sqlite+aiosqlite:///zstyle.db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} # Needed for SQLite
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
