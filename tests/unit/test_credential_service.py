"""
Unit tests for CredentialService.

Following TDD principles - these tests are written before implementation.
Tests use real database and real encryption (no mocks).
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any

from core.database.engine import Base
from core.database.models import User, Credential
from services.credential_service import CredentialNotFoundError


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
async def test_user(db_session):
    """Create a test user."""
    user = User(telegram_id=12345, username="testuser")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def credential_service(db_session):
    """Create a CredentialService instance with test database session."""
    # Import will fail until service is created - expected in TDD
    try:
        from services.credential_service import CredentialService
        service = CredentialService()
        # Store session for use in tests - create a wrapper that auto-passes session
        original_store = service.store_credentials
        original_get = service.get_credentials
        original_update = service.update_credentials
        original_delete = service.delete_credentials
        
        async def store_wrapper(*args, **kwargs):
            kwargs['session'] = db_session
            return await original_store(*args, **kwargs)
        
        async def get_wrapper(*args, **kwargs):
            kwargs['session'] = db_session
            return await original_get(*args, **kwargs)
        
        async def update_wrapper(*args, **kwargs):
            kwargs['session'] = db_session
            return await original_update(*args, **kwargs)
        
        async def delete_wrapper(*args, **kwargs):
            kwargs['session'] = db_session
            return await original_delete(*args, **kwargs)
        
        service.store_credentials = store_wrapper
        service.get_credentials = get_wrapper
        service.update_credentials = update_wrapper
        service.delete_credentials = delete_wrapper
        
        return service
    except ImportError:
        pytest.skip("CredentialService not yet implemented")


# ============================================================================
# STORE CREDENTIALS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_store_credentials_with_token_only(credential_service, test_user):
    """Test storing credentials with only a token."""
    credentials = {"token": "test_access_token"}
    
    result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    assert result is not None
    assert result.user_id == test_user.id
    assert result.credential_type == "google"
    assert result.token_value is not None
    assert result.token_value != "test_access_token"  # Should be encrypted
    assert result.refresh_token is None
    assert result.extra_data == {}


@pytest.mark.asyncio
async def test_store_credentials_with_refresh_token(credential_service, test_user):
    """Test storing credentials with token and refresh_token."""
    credentials = {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token"
    }
    
    result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    assert result is not None
    assert result.refresh_token is not None
    assert result.refresh_token != "test_refresh_token"  # Should be encrypted


@pytest.mark.asyncio
async def test_store_credentials_with_metadata(credential_service, test_user):
    """Test storing credentials with metadata (scopes, expires_in, etc.)."""
    credentials = {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "scope": "read write",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
    
    result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    assert result is not None
    # Metadata should be in extra_data (unencrypted)
    assert result.extra_data["scope"] == "read write"
    assert result.extra_data["expires_in"] == 3600
    assert result.extra_data["token_type"] == "Bearer"
    # Token should not be in extra_data
    assert "token" not in result.extra_data
    assert "refresh_token" not in result.extra_data


@pytest.mark.asyncio
async def test_store_credentials_missing_token(credential_service, test_user):
    """Test that storing credentials without token raises error."""
    credentials = {"scope": "read write"}  # Missing token
    
    with pytest.raises(ValueError, match="token"):
        await credential_service.store_credentials(
            user_id=test_user.id,
            service="google",
            credentials=credentials
        )


@pytest.mark.asyncio
async def test_store_credentials_multiple_services(credential_service, test_user):
    """Test storing multiple credentials for same user (different services)."""
    google_creds = {"token": "google_token"}
    telegram_creds = {"token": "telegram_token"}
    
    google_result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=google_creds
    )
    
    telegram_result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="telegram",
        credentials=telegram_creds
    )
    
    assert google_result.id != telegram_result.id
    assert google_result.credential_type == "google"
    assert telegram_result.credential_type == "telegram"


# ============================================================================
# RETRIEVE CREDENTIALS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_credentials_success(credential_service, test_user):
    """Test retrieving stored credentials."""
    # Store first
    original_creds = {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "scope": "read write"
    }
    
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=original_creds
    )
    
    # Retrieve
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved is not None
    assert retrieved["token"] == "test_access_token"
    assert retrieved["refresh_token"] == "test_refresh_token"
    assert retrieved["scope"] == "read write"


@pytest.mark.asyncio
async def test_get_credentials_not_found(credential_service, test_user):
    """Test retrieving non-existent credentials returns None."""
    result = await credential_service.get_credentials(
        user_id=test_user.id,
        service="nonexistent"
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_get_credentials_encrypt_decrypt_roundtrip(credential_service, test_user):
    """Test that encryption/decryption works correctly (roundtrip)."""
    original_token = "very_secret_token_12345"
    credentials = {"token": original_token}
    
    # Store
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    # Retrieve
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["token"] == original_token


@pytest.mark.asyncio
async def test_get_credentials_without_refresh_token(credential_service, test_user):
    """Test retrieving credentials that don't have refresh_token."""
    credentials = {"token": "test_token"}
    
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["token"] == "test_token"
    assert "refresh_token" not in retrieved or retrieved.get("refresh_token") is None


# ============================================================================
# UPDATE CREDENTIALS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_credentials_existing(credential_service, test_user):
    """Test updating existing credentials."""
    # Store initial
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "old_token", "scope": "read"}
    )
    
    # Update
    updated_result = await credential_service.update_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "new_token", "scope": "read write"}
    )
    
    assert updated_result is not None
    
    # Verify update
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["token"] == "new_token"
    assert retrieved["scope"] == "read write"


@pytest.mark.asyncio
async def test_update_credentials_not_found(credential_service, test_user):
    """Test updating non-existent credentials raises error."""
    with pytest.raises(CredentialNotFoundError):
        await credential_service.update_credentials(
            user_id=test_user.id,
            service="nonexistent",
            credentials={"token": "new_token"}
        )


@pytest.mark.asyncio
async def test_update_credentials_add_refresh_token(credential_service, test_user):
    """Test updating credentials to add refresh_token."""
    # Store without refresh_token
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "access_token"}
    )
    
    # Update with refresh_token
    await credential_service.update_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "access_token", "refresh_token": "new_refresh"}
    )
    
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["refresh_token"] == "new_refresh"


# ============================================================================
# DELETE CREDENTIALS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delete_credentials_success(credential_service, test_user):
    """Test deleting credentials."""
    # Store first
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "test_token"}
    )
    
    # Delete
    await credential_service.delete_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    # Verify deleted
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_credentials_not_found(credential_service, test_user):
    """Test deleting non-existent credentials raises error."""
    with pytest.raises(CredentialNotFoundError):
        await credential_service.delete_credentials(
            user_id=test_user.id,
            service="nonexistent"
        )


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_store_credentials_overwrites_existing(credential_service, test_user):
    """Test that storing credentials for same user/service overwrites existing."""
    # Store first
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "first_token"}
    )
    
    # Store again (should overwrite)
    await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials={"token": "second_token"}
    )
    
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["token"] == "second_token"


@pytest.mark.asyncio
async def test_credentials_isolation_between_users(credential_service, db_session):
    """Test that credentials are isolated between different users."""
    user1 = User(telegram_id=11111, username="user1")
    user2 = User(telegram_id=22222, username="user2")
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)
    
    # Store for user1
    await credential_service.store_credentials(
        user_id=user1.id,
        service="google",
        credentials={"token": "user1_token"}
    )
    
    # Store for user2
    await credential_service.store_credentials(
        user_id=user2.id,
        service="google",
        credentials={"token": "user2_token"}
    )
    
    # Retrieve each
    user1_creds = await credential_service.get_credentials(
        user_id=user1.id,
        service="google"
    )
    user2_creds = await credential_service.get_credentials(
        user_id=user2.id,
        service="google"
    )
    
    assert user1_creds["token"] == "user1_token"
    assert user2_creds["token"] == "user2_token"


@pytest.mark.asyncio
async def test_credentials_empty_metadata(credential_service, test_user):
    """Test storing credentials with only token (no metadata)."""
    credentials = {"token": "simple_token"}
    
    result = await credential_service.store_credentials(
        user_id=test_user.id,
        service="google",
        credentials=credentials
    )
    
    assert result.extra_data == {}
    
    retrieved = await credential_service.get_credentials(
        user_id=test_user.id,
        service="google"
    )
    
    assert retrieved["token"] == "simple_token"
    assert len(retrieved) == 1  # Only token, no other keys
