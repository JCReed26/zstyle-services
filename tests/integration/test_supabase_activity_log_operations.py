"""
Integration tests for ActivityLog operations against Supabase database.
"""
import pytest
from datetime import datetime, timezone
from database.repositories import UserRepository
from database.models import ActivityLog, ActivityLogSource
from services.activity_log import activity_log_service


@pytest.mark.asyncio
async def test_create_activity_log(db_session):
    """Test creating an activity log entry."""
    # Arrange
    user_repo = UserRepository(db_session)
    user = await user_repo.create(telegram_id=90000, username="log_test")
    
    # Act
    log_entry = await activity_log_service.log(
        user_id=user.id,
        source=ActivityLogSource.TELEGRAM,
        action="user sent message: Hello, world!",
        extra_data={"message_length": 13}
    )
    
    # Assert
    assert log_entry.id is not None
    assert log_entry.user_id == user.id
    assert log_entry.source == ActivityLogSource.TELEGRAM.value
    assert log_entry.action == "user sent message: Hello, world!"
    assert log_entry.extra_data == {"message_length": 13}
    assert log_entry.timestamp is not None


@pytest.mark.asyncio
async def test_retrieve_recent_activity_logs(db_session):
    """Test retrieving recent activity logs for a user."""
    # Arrange
    user_repo = UserRepository(db_session)
    user = await user_repo.create(telegram_id=100000, username="recent_logs_test")
    
    # Create multiple log entries
    for i in range(5):
        await activity_log_service.log(
            user_id=user.id,
            source=ActivityLogSource.SYSTEM,
            action=f"Test action {i}",
            extra_data={"index": i}
        )
    
    # Act - Retrieve recent logs
    recent_logs = await activity_log_service.get_recent(user_id=user.id, limit=5)
    
    # Assert - Verify logs are returned in correct order (most recent first)
    assert len(recent_logs) == 5
    assert recent_logs[0].action == "Test action 4"  # Most recent
    assert recent_logs[4].action == "Test action 0"  # Oldest
    for i, log in enumerate(recent_logs):
        assert log.user_id == user.id
        assert log.source == ActivityLogSource.SYSTEM.value


@pytest.mark.asyncio
async def test_activity_log_source_filter(db_session):
    """Test filtering activity logs by source."""
    # Arrange
    user_repo = UserRepository(db_session)
    user = await user_repo.create(telegram_id=110000, username="filter_test")
    
    # Create logs from different sources
    await activity_log_service.log(
        user_id=user.id,
        source=ActivityLogSource.TELEGRAM,
        action="Telegram message"
    )
    await activity_log_service.log(
        user_id=user.id,
        source=ActivityLogSource.SYSTEM,
        action="System event"
    )
    await activity_log_service.log(
        user_id=user.id,
        source=ActivityLogSource.TELEGRAM,
        action="Another Telegram message"
    )
    
    # Act - Filter by source
    telegram_logs = await activity_log_service.get_recent(
        user_id=user.id,
        limit=10,
        source_filter=ActivityLogSource.TELEGRAM
    )
    
    # Assert
    assert len(telegram_logs) == 2
    for log in telegram_logs:
        assert log.source == ActivityLogSource.TELEGRAM.value
