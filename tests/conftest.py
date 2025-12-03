import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock env vars before importing main
os.environ["TELEGRAM_BOT_TOKEN"] = "mock_token"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from main import app
from database.sqlite_db import get_db_session

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def mock_db_session():
    # In a real test, we might use a sqlite in-memory db.
    # For now, let's mock the session dependency to avoid DB setup complexity in this environment.
    mock_session = MagicMock(spec=AsyncSession)
    
    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_get_db
    yield mock_session
    app.dependency_overrides = {}
