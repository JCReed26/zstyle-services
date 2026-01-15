"""
Unit tests for database repository pattern.

Following TDD principles - these tests are written before implementation.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.database.engine import Base
from core.database.repositories import UserRepository
from core.database.models import User


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()
    
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def user_repository(db_session):
    """Create a UserRepository instance."""
    return UserRepository(db_session)


@pytest.mark.asyncio
async def test_user_repository_create(user_repository):
    """Test creating a new user."""
    user = await user_repository.create(telegram_id=12345, username="testuser")
    
    assert user.id is not None
    assert user.telegram_id == 12345
    assert user.username == "testuser"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_repository_create_with_all_fields(user_repository):
    """Test creating a user with all fields."""
    user = await user_repository.create(
        telegram_id=67890,
        username="fulluser",
        display_name="Full User",
        email="user@example.com",
        is_active=True
    )
    
    assert user.id is not None
    assert user.telegram_id == 67890
    assert user.username == "fulluser"
    assert user.display_name == "Full User"
    assert user.email == "user@example.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_repository_get_by_telegram_id(user_repository):
    """Test retrieving a user by telegram_id."""
    # Create a user first
    created_user = await user_repository.create(telegram_id=11111, username="getuser")
    
    # Retrieve it
    found_user = await user_repository.get_by_telegram_id(11111)
    
    assert found_user is not None
    assert found_user.id == created_user.id
    assert found_user.telegram_id == 11111
    assert found_user.username == "getuser"


@pytest.mark.asyncio
async def test_user_repository_get_by_telegram_id_not_found(user_repository):
    """Test retrieving a non-existent user returns None."""
    found_user = await user_repository.get_by_telegram_id(99999)
    assert found_user is None


@pytest.mark.asyncio
async def test_user_repository_get_by_id(user_repository):
    """Test retrieving a user by internal ID."""
    # Create a user first
    created_user = await user_repository.create(telegram_id=22222, username="iduser")
    user_id = created_user.id
    
    # Retrieve it
    found_user = await user_repository.get_by_id(user_id)
    
    assert found_user is not None
    assert found_user.id == user_id
    assert found_user.telegram_id == 22222


@pytest.mark.asyncio
async def test_user_repository_get_by_id_not_found(user_repository):
    """Test retrieving a non-existent user by ID returns None."""
    found_user = await user_repository.get_by_id("nonexistent-id")
    assert found_user is None


@pytest.mark.asyncio
async def test_user_repository_update(user_repository):
    """Test updating a user."""
    # Create a user
    user = await user_repository.create(telegram_id=33333, username="oldname")
    
    # Update it
    updated_user = await user_repository.update(
        user.id,
        username="newname",
        display_name="New Display Name"
    )
    
    assert updated_user.username == "newname"
    assert updated_user.display_name == "New Display Name"
    assert updated_user.telegram_id == 33333  # Unchanged


@pytest.mark.asyncio
async def test_user_repository_update_not_found(user_repository):
    """Test updating a non-existent user raises error."""
    with pytest.raises(ValueError, match="User not found"):
        await user_repository.update("nonexistent-id", username="new")


@pytest.mark.asyncio
async def test_user_repository_delete(user_repository):
    """Test deleting a user."""
    # Create a user
    user = await user_repository.create(telegram_id=44444, username="todelete")
    user_id = user.id
    
    # Delete it
    await user_repository.delete(user_id)
    
    # Verify it's gone
    found_user = await user_repository.get_by_id(user_id)
    assert found_user is None


@pytest.mark.asyncio
async def test_user_repository_delete_not_found(user_repository):
    """Test deleting a non-existent user raises error."""
    with pytest.raises(ValueError, match="User not found"):
        await user_repository.delete("nonexistent-id")


@pytest.mark.asyncio
async def test_user_repository_duplicate_telegram_id(user_repository):
    """Test that creating duplicate telegram_id raises error."""
    await user_repository.create(telegram_id=55555, username="first")
    
    # Attempt to create another user with same telegram_id
    # SQLite raises IntegrityError, but we need to commit the first one first
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):  # Should raise IntegrityError
        await user_repository.create(telegram_id=55555, username="duplicate")


@pytest.mark.asyncio
async def test_user_repository_create_with_null_username(user_repository):
    """Test creating a user with null username is allowed."""
    user = await user_repository.create(telegram_id=66666, username=None)
    assert user.id is not None
    assert user.telegram_id == 66666
    assert user.username is None
