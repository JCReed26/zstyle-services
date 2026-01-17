"""
Integration tests for Credential operations against Supabase database.

These tests verify secure credential storage and retrieval.
"""
import pytest
from datetime import datetime, timezone, timedelta
from database.repositories import CredentialRepository, UserRepository
from database.models import Credential, CredentialType
from app.security import encrypt_credential, decrypt_credential


@pytest.mark.asyncio
async def test_create_encrypted_credential(db_session):
    """Test creating an encrypted credential in Supabase."""
    # Arrange
    user_repo = UserRepository(db_session)
    cred_repo = CredentialRepository(db_session)
    
    user = await user_repo.create(telegram_id=50000, username="cred_test_user")
    encrypted_token = encrypt_credential("test_token_value_12345")
    
    # Act
    credential = await cred_repo.create(
        user_id=user.id,
        credential_type=CredentialType.GOOGLE_OAUTH,
        token_value=encrypted_token,
        refresh_token=encrypt_credential("refresh_token_67890"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    
    # Assert
    assert credential.id is not None
    assert credential.user_id == user.id
    assert credential.credential_type == CredentialType.GOOGLE_OAUTH
    assert credential.token_value == encrypted_token  # Stored encrypted
    assert credential.expires_at is not None
    assert credential.is_active is True


@pytest.mark.asyncio
async def test_retrieve_and_decrypt_credential(db_session):
    """Test retrieving and decrypting a credential."""
    # Arrange
    user_repo = UserRepository(db_session)
    cred_repo = CredentialRepository(db_session)
    
    user = await user_repo.create(telegram_id=60000, username="decrypt_test")
    original_token = "secret_token_abc123"
    encrypted_token = encrypt_credential(original_token)
    
    credential = await cred_repo.create(
        user_id=user.id,
        credential_type=CredentialType.TICKTICK_TOKEN,
        token_value=encrypted_token
    )
    
    # Act - Retrieve credential
    found_cred = await cred_repo.get_by_user_and_type(
        user.id,
        CredentialType.TICKTICK_TOKEN
    )
    
    # Decrypt the token
    decrypted_token = decrypt_credential(found_cred.token_value)
    
    # Assert
    assert found_cred is not None
    assert decrypted_token == original_token
    assert found_cred.token_value != original_token  # Verify it's encrypted


@pytest.mark.asyncio
async def test_credential_expiration_check(db_session):
    """Test credential expiration checking."""
    # Arrange
    user_repo = UserRepository(db_session)
    cred_repo = CredentialRepository(db_session)
    
    user = await user_repo.create(telegram_id=70000, username="expiry_test")
    
    # Create expired credential
    expired_cred = await cred_repo.create(
        user_id=user.id,
        credential_type=CredentialType.GOOGLE_OAUTH,
        token_value=encrypt_credential("expired_token"),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired 1 hour ago
    )
    
    # Create non-expired credential
    valid_cred = await cred_repo.create(
        user_id=user.id,
        credential_type=CredentialType.TICKTICK_TOKEN,
        token_value=encrypt_credential("valid_token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)  # Expires in 1 hour
    )
    
    # Act & Assert
    assert expired_cred.is_expired() is True
    assert valid_cred.is_expired() is False


@pytest.mark.asyncio
async def test_update_credential_token(db_session):
    """Test updating a credential's token value."""
    # Arrange
    user_repo = UserRepository(db_session)
    cred_repo = CredentialRepository(db_session)
    
    user = await user_repo.create(telegram_id=80000, username="update_test")
    old_token = encrypt_credential("old_token")
    
    credential = await cred_repo.create(
        user_id=user.id,
        credential_type=CredentialType.GOOGLE_OAUTH,
        token_value=old_token
    )
    
    # Act - Update with new token
    new_token = encrypt_credential("new_token_after_refresh")
    updated_cred = await cred_repo.update(
        credential.id,
        token_value=new_token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
    )
    
    # Assert
    assert updated_cred.token_value == new_token
    assert decrypt_credential(updated_cred.token_value) == "new_token_after_refresh"
    assert updated_cred.expires_at > datetime.now(timezone.utc)
