"""
Shared pytest fixtures for all tests.

This module provides common fixtures used across the test suite, including:
- Event loop management for async tests
- Database session fixtures with in-memory SQLite
- Proper cleanup and isolation between tests
- Environment variable setup for tests
"""
# CRITICAL: Set environment variables BEFORE any imports that use settings
import os
os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-bot-token")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long")

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.database.engine import Base
from core.config import reset_settings

# Reset settings singleton to pick up test environment variables
reset_settings()


# Test database setup - using in-memory SQLite for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.
    
    This fixture ensures pytest-asyncio has a proper event loop to work with.
    The session scope means the loop is reused across all tests in the session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """
    Create a test database session with automatic cleanup.
    
    This fixture:
    - Creates all database tables before the test
    - Provides a fresh database session for each test
    - Rolls back any uncommitted changes after the test
    - Drops all tables after the test completes
    
    Each test gets a completely fresh database state, ensuring test isolation.
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()
    
    # Cleanup - drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
