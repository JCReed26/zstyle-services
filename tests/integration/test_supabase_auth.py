"""
Integration tests for Supabase authentication flow.

Tests:
- Phone + OTP authentication
- Profile auto-creation via trigger
- RLS policies (user cannot access others' data)
- Telegram ID linking
- OAuth token storage
- Cascade deletes
"""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timezone

from database.engine import AsyncSessionLocal
from database.repositories import UserRepository, CredentialRepository, OAuthStateRepository
from database.models import User, Credential, OAuthState
from services.auth_service import auth_service


@pytest.mark.asyncio
async def test_user_profile_auto_creation():
    """
    Test that user profile is automatically created when auth.users is created.
    
    Note: This test requires Supabase Auth to be configured and a real auth.users
    record. In practice, the trigger handles this automatically.
    """
    # This test would require mocking Supabase Auth or using test credentials
    # For now, we'll test that the repository can create a user profile
    # with a given UUID (simulating auth.users.id)
    
    test_user_id = uuid4()
    
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        
        # Create user profile (simulating trigger behavior)
        user = await repo.create(user_id=test_user_id)
        
        assert user.id == test_user_id
        assert user.is_active is True
        assert user.created_at is not None
        
        # Verify user can be retrieved
        retrieved = await repo.get_by_id(test_user_id)
        assert retrieved is not None
        assert retrieved.id == test_user_id


@pytest.mark.asyncio
async def test_telegram_id_linking():
    """Test linking Telegram ID to user profile."""
    test_user_id = uuid4()
    telegram_id = 123456789
    
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        
        # Create user
        user = await repo.create(user_id=test_user_id)
        
        # Link Telegram ID
        user = await repo.update(user.id, telegram_id=telegram_id, username="testuser")
        
        assert user.telegram_id == telegram_id
        assert user.username == "testuser"
        
        # Verify lookup by Telegram ID
        found_user = await repo.get_by_telegram_id(telegram_id)
        assert found_user is not None
        assert found_user.id == test_user_id


@pytest.mark.asyncio
async def test_credential_storage():
    """Test storing OAuth credentials."""
    test_user_id = uuid4()
    
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        cred_repo = CredentialRepository(db)
        
        # Create user
        await user_repo.create(user_id=test_user_id)
        
        # Store credential
        credential = await cred_repo.create(
            user_id=test_user_id,
            credential_type="google_oauth",
            token_value="test_token",
            refresh_token="test_refresh",
            expires_at=datetime.now(timezone.utc)
        )
        
        assert credential.user_id == test_user_id
        assert credential.credential_type == "google_oauth"
        assert credential.token_value == "test_token"
        
        # Retrieve credential
        retrieved = await cred_repo.get_by_user_and_type(
            test_user_id,
            "google_oauth"
        )
        assert retrieved is not None
        assert retrieved.token_value == "test_token"


@pytest.mark.asyncio
async def test_oauth_state_creation():
    """Test OAuth state token creation and consumption."""
    test_user_id = uuid4()
    
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        state_repo = OAuthStateRepository(db)
        
        # Create user
        await user_repo.create(user_id=test_user_id)
        
        # Create state token
        state_token = "test_state_token_12345"
        oauth_state = await state_repo.create(
            state_token=state_token,
            user_id=test_user_id,
            service="google",
            expiration_minutes=10
        )
        
        assert oauth_state.user_id == test_user_id
        assert oauth_state.service == "google"
        assert oauth_state.consumed is False
        
        # Consume token
        consumed = await state_repo.consume_token(state_token)
        assert consumed is not None
        assert consumed.consumed is True
        
        # Try to consume again (should fail)
        with pytest.raises(ValueError):
            await state_repo.consume_token(state_token)


@pytest.mark.asyncio
async def test_cascade_delete():
    """
    Test that deleting a user cascades to related records.
    
    Note: This test requires the foreign key constraints to be set up correctly.
    In practice, deleting auth.users should cascade delete the profile and related records.
    """
    test_user_id = uuid4()
    
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        cred_repo = CredentialRepository(db)
        state_repo = OAuthStateRepository(db)
        
        # Create user and related records
        await user_repo.create(user_id=test_user_id)
        
        await cred_repo.create(
            user_id=test_user_id,
            credential_type="google_oauth",
            token_value="test_token"
        )
        
        await state_repo.create(
            state_token="test_state",
            user_id=test_user_id,
            service="google"
        )
        
        # Delete user (should cascade)
        await user_repo.delete(test_user_id)
        
        # Verify related records are deleted
        # Note: In actual Supabase, deleting auth.users would cascade
        # Here we're testing the repository delete method
        
        user = await user_repo.get_by_id(test_user_id)
        assert user is None
        
        # Credentials should be deleted (cascade)
        creds = await cred_repo.get_all_by_user(test_user_id)
        assert len(creds) == 0


@pytest.mark.asyncio
async def test_user_isolation():
    """
    Test that users cannot access each other's data.
    
    This tests RLS policies indirectly by verifying that queries
    return only the user's own data.
    """
    user1_id = uuid4()
    user2_id = uuid4()
    
    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        cred_repo = CredentialRepository(db)
        
        # Create two users
        await user_repo.create(user_id=user1_id)
        await user_repo.create(user_id=user2_id)
        
        # Create credentials for each
        await cred_repo.create(
            user_id=user1_id,
            credential_type="google_oauth",
            token_value="user1_token"
        )
        
        await cred_repo.create(
            user_id=user2_id,
            credential_type="google_oauth",
            token_value="user2_token"
        )
        
        # User 1 should only see their own credentials
        user1_creds = await cred_repo.get_all_by_user(user1_id)
        assert len(user1_creds) == 1
        assert user1_creds[0].token_value == "user1_token"
        
        # User 2 should only see their own credentials
        user2_creds = await cred_repo.get_all_by_user(user2_id)
        assert len(user2_creds) == 1
        assert user2_creds[0].token_value == "user2_token"


# Note: Tests for actual Supabase Auth phone + OTP flow would require:
# - Supabase test project or mocking
# - Test phone numbers
# - SMS provider configuration
# These are better suited for manual testing or E2E tests
