"""
Integration tests for User operations against Supabase database.

These tests verify that User CRUD operations work correctly with Supabase PostgreSQL.
Run with: pytest tests/integration/test_supabase_user_operations.py -v

Requires TEST_DATABASE_URL environment variable set to Supabase connection string.
"""
import pytest
from database.repositories import UserRepository
from database.models import User


@pytest.mark.asyncio
async def test_create_user_in_supabase(db_session):
    """Test creating a user in Supabase database."""
    # Arrange
    repository = UserRepository(db_session)
    
    # Act
    user = await repository.create(
        telegram_id=12345,
        username="testuser_supabase",
        email="test@example.com"
    )
    
    # Assert
    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.username == "testuser_supabase"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_retrieve_user_by_telegram_id(db_session):
    """Test retrieving a user by Telegram ID from Supabase."""
    # Arrange
    repository = UserRepository(db_session)
    created_user = await repository.create(
        telegram_id=67890,
        username="retrieve_test"
    )
    
    # Act
    found_user = await repository.get_by_telegram_id(67890)
    
    # Assert
    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.telegram_id == 67890


@pytest.mark.asyncio
async def test_update_user_in_supabase(db_session):
    """Test updating a user in Supabase."""
    # Arrange
    repository = UserRepository(db_session)
    user = await repository.create(
        telegram_id=11111,
        username="oldname"
    )
    
    # Act
    updated_user = await repository.update(
        user.id,
        username="newname",
        display_name="New Display Name"
    )
    
    # Assert
    assert updated_user.username == "newname"
    assert updated_user.display_name == "New Display Name"
    assert updated_user.telegram_id == 11111  # Unchanged


@pytest.mark.asyncio
async def test_multiple_users_isolation(db_session):
    """Test that multiple users can coexist in Supabase."""
    # Arrange
    repository = UserRepository(db_session)
    
    # Act - Create multiple users
    user1 = await repository.create(telegram_id=100, username="user1")
    user2 = await repository.create(telegram_id=200, username="user2")
    user3 = await repository.create(telegram_id=300, username="user3")
    
    # Assert - Verify all users exist and are distinct
    found_user1 = await repository.get_by_telegram_id(100)
    found_user2 = await repository.get_by_telegram_id(200)
    found_user3 = await repository.get_by_telegram_id(300)
    
    assert found_user1.id != found_user2.id
    assert found_user2.id != found_user3.id
    assert found_user1.username == "user1"
    assert found_user2.username == "user2"
    assert found_user3.username == "user3"


@pytest.mark.asyncio
async def test_user_timestamps_auto_populated(db_session):
    """Test that created_at and updated_at are automatically populated."""
    # Arrange
    repository = UserRepository(db_session)
    
    # Act
    user = await repository.create(telegram_id=99999, username="timestamp_test")
    
    # Assert
    assert user.created_at is not None
    assert user.updated_at is not None
    # Verify timestamps are timezone-aware (PostgreSQL returns timezone-aware datetimes)
    assert user.created_at.tzinfo is not None
