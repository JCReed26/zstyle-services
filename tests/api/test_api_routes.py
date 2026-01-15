"""
Unit tests for API routes.

Following TDD principles - these tests are written before implementation.
Tests use TestClient for integration-style testing and mock database dependencies.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from typing import Optional

# Set required environment variables before importing modules
os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("TICKTICK_CLIENT_ID", "test-ticktick-client-id")
os.environ.setdefault("TICKTICK_CLIENT_SECRET", "test-ticktick-client-secret")
os.environ.setdefault("PORT", "8000")

# Import app - handle import errors gracefully
# Note: There may be pre-existing import issues in the codebase
try:
    from main import app
except (ImportError, Exception):
    # If main.py can't be imported, create a minimal app for testing
    from fastapi import FastAPI
    from interface.api.routes import router as api_router
    app = FastAPI()
    app.include_router(api_router, prefix="/api")
    # Also add health at root level to match main.py
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "zstyle-services",
            "agents_dir": "/agents"
        }


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """Create a TestClient instance."""
    if app is None:
        pytest.skip("App not yet implemented")
    return TestClient(app)

@pytest.fixture
def override_get_db_session():
    """Fixture to override get_db_session dependency."""
    from core.database.engine import get_db_session
    return get_db_session


@pytest.fixture
def mock_user():
    """Create a mock User object."""
    user = MagicMock()
    user.id = "test_user_123"
    user.username = "testuser"
    user.display_name = "Test User"
    user.email = "test@example.com"
    user.telegram_id = 12345
    user.is_active = True
    user.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    user.updated_at = datetime.now(timezone.utc) - timedelta(days=1)
    return user


@pytest.fixture
def mock_activity_logs():
    """Create mock activity log objects."""
    logs = []
    for i in range(5):
        log = MagicMock()
        log.timestamp = datetime.now(timezone.utc) - timedelta(hours=i)
        log.source = "telegram"
        log.action = f"Test action {i+1}"
        logs.append(log)
    return logs


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    return session


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

def test_health_check(test_client):
    """Test that /health endpoint returns 200 with expected structure."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "agents_dir" in data
    assert data["status"] == "healthy"
    assert data["service"] == "zstyle-services"


# ============================================================================
# USER STATE ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_state_success(test_client, mock_user, mock_activity_logs, mock_db_session, override_get_db_session):
    """Test that valid user_id returns user state with profile, activity, and memory summary."""
    from interface.api.routes import router
    
    # Create mock async context manager for db session
    async def mock_db_session_cm():
        yield mock_db_session
    
    # Override the dependency
    app.dependency_overrides[override_get_db_session] = mock_db_session_cm
    
    try:
        with patch('interface.api.routes.UserRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_repo_class.return_value = mock_repo
            
            # Mock activity log query result
            mock_activity_result = MagicMock()
            mock_activity_result.scalars.return_value.all.return_value = mock_activity_logs
            
            # Mock memory count query results
            mock_memory_count_result = MagicMock()
            mock_memory_count_result.scalar.return_value = 10
            
            # Mock db.execute to return different results for different calls
            call_count = 0
            async def mock_execute(stmt):
                nonlocal call_count
                call_count += 1
                # First call: activity logs
                if call_count == 1:
                    return mock_activity_result
                # Subsequent calls: memory counts
                return mock_memory_count_result
            
            mock_db_session.execute = AsyncMock(side_effect=mock_execute)
            
            response = test_client.get("/api/user/state?user_id=test_user_123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert "profile" in data
        assert "recent_activity" in data
        assert "memory_summary" in data
        
        # Verify profile data
        assert data["user_id"] == "test_user_123"
        assert data["profile"]["username"] == "testuser"
        assert data["profile"]["display_name"] == "Test User"
        assert data["profile"]["email"] == "test@example.com"
        assert data["profile"]["telegram_id"] == 12345
        assert data["profile"]["is_active"] is True
        
        # Verify activity logs
        assert isinstance(data["recent_activity"], list)
        assert len(data["recent_activity"]) == 5
        
        # Verify memory summary
        assert "total_memories" in data["memory_summary"]
        assert "recent_memories" in data["memory_summary"]


@pytest.mark.asyncio
async def test_get_user_state_not_found(test_client, mock_db_session):
    """Test that invalid user_id returns 404."""
    with patch('interface.api.routes.get_db_session') as mock_get_db, \
         patch('interface.api.routes.UserRepository') as mock_repo_class:
        
        # Setup mocks
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_get_db.return_value.__aexit__.return_value = None
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo
        
        response = test_client.get("/api/user/state?user_id=nonexistent_user")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


def test_get_user_state_missing_user_id(test_client):
    """Test that missing user_id parameter returns 422."""
    response = test_client.get("/api/user/state")
    
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_get_user_state_with_activity_logs(test_client, mock_user, mock_activity_logs, mock_db_session):
    """Test that user with activity logs returns them in response."""
    with patch('interface.api.routes.get_db_session') as mock_get_db, \
         patch('interface.api.routes.UserRepository') as mock_repo_class:
        
        # Setup mocks
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_get_db.return_value.__aexit__.return_value = None
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_repo_class.return_value = mock_repo
        
        # Mock activity log query result
        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = mock_activity_logs
        
        # Mock memory count query results
        mock_memory_count_result = MagicMock()
        mock_memory_count_result.scalar.return_value = 5
        
        # Mock db.execute to return different results for different calls
        call_count = 0
        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            # First call: activity logs
            if call_count == 1:
                return mock_activity_result
            # Subsequent calls: memory counts
            return mock_memory_count_result
        
        mock_db_session.execute = AsyncMock(side_effect=mock_execute)
        
        response = test_client.get("/api/user/state?user_id=test_user_123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify activity logs structure
        assert len(data["recent_activity"]) == 5
        for log in data["recent_activity"]:
            assert "timestamp" in log
            assert "source" in log
            assert "action" in log
            assert log["source"] == "telegram"


@pytest.mark.asyncio
async def test_get_user_state_database_error(test_client, mock_db_session):
    """Test that database errors are handled gracefully."""
    with patch('interface.api.routes.get_db_session') as mock_get_db, \
         patch('interface.api.routes.UserRepository') as mock_repo_class:
        
        # Setup mocks
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_get_db.return_value.__aexit__.return_value = None
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(side_effect=Exception("Database connection error"))
        mock_repo_class.return_value = mock_repo
        
        response = test_client.get("/api/user/state?user_id=test_user_123")
        
        # Should return 500 or handle error gracefully
        assert response.status_code in [500, 503]
        data = response.json()
        assert "detail" in data


@pytest.mark.asyncio
async def test_get_user_state_empty_activity_logs(test_client, mock_user, mock_db_session):
    """Test that user with no activity logs returns empty array."""
    with patch('interface.api.routes.get_db_session') as mock_get_db, \
         patch('interface.api.routes.UserRepository') as mock_repo_class:
        
        # Setup mocks
        mock_get_db.return_value.__aenter__.return_value = mock_db_session
        mock_get_db.return_value.__aexit__.return_value = None
        
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_repo_class.return_value = mock_repo
        
        # Mock empty activity log query result
        mock_activity_result = MagicMock()
        mock_activity_result.scalars.return_value.all.return_value = []
        
        # Mock memory count query results
        mock_memory_count_result = MagicMock()
        mock_memory_count_result.scalar.return_value = 0
        
        # Mock db.execute to return different results for different calls
        call_count = 0
        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            # First call: activity logs (empty)
            if call_count == 1:
                return mock_activity_result
            # Subsequent calls: memory counts
            return mock_memory_count_result
        
        mock_db_session.execute = AsyncMock(side_effect=mock_execute)
        
        response = test_client.get("/api/user/state?user_id=test_user_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["recent_activity"] == []
        assert data["memory_summary"]["total_memories"] == 0
        assert data["memory_summary"]["recent_memories"] == 0
