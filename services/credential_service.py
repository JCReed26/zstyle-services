"""
Credential Service

Provides secure storage and retrieval of user credentials.
Encrypts sensitive tokens while storing non-sensitive metadata unencrypted.

USAGE EXAMPLE:
==============
from services.credential_service import credential_service

# Store credentials
await credential_service.store_credentials(
    user_id="user123",
    service="google",
    credentials={
        "token": "access_token",
        "refresh_token": "refresh_token",
        "scope": "read write"
    }
)

# Retrieve credentials
creds = await credential_service.get_credentials(
    user_id="user123",
    service="google"
)
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.engine import AsyncSessionLocal
from core.database.repositories import CredentialRepository
from core.security import encrypt_credential, decrypt_credential


class CredentialNotFoundError(Exception):
    """Raised when a credential is not found."""
    pass


class CredentialService:
    """
    Service for managing user credentials securely.
    
    Handles encryption/decryption of sensitive tokens and storage
    of non-sensitive metadata. All sensitive data (tokens, API keys)
    are encrypted at rest.
    """
    
    # Sensitive keys that should be encrypted
    SENSITIVE_KEYS = {"token", "refresh_token", "api_key", "secret", "password"}
    
    def _extract_sensitive_data(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract sensitive data from credentials dict.
        
        Args:
            credentials: Dictionary of credential data
            
        Returns:
            Dictionary with 'token_value' and 'refresh_token' (encrypted),
            and 'extra_data' (non-sensitive metadata)
        """
        if "token" not in credentials:
            raise ValueError("credentials must contain 'token' key")
        
        # Extract and encrypt sensitive data
        token_value = encrypt_credential(str(credentials["token"]))
        
        refresh_token = None
        if "refresh_token" in credentials and credentials["refresh_token"]:
            refresh_token = encrypt_credential(str(credentials["refresh_token"]))
        
        # Extract non-sensitive metadata
        extra_data = {
            k: v for k, v in credentials.items()
            if k not in self.SENSITIVE_KEYS
        }
        
        return {
            "token_value": token_value,
            "refresh_token": refresh_token,
            "extra_data": extra_data
        }
    
    def _reconstruct_credentials(
        self,
        credential
    ) -> Dict[str, Any]:
        """
        Reconstruct credentials dict from Credential model.
        
        Args:
            credential: Credential model instance
            
        Returns:
            Dictionary with decrypted tokens and metadata
        """
        result = {}
        
        # Decrypt token
        if credential.token_value:
            result["token"] = decrypt_credential(credential.token_value)
        
        # Decrypt refresh_token if present
        if credential.refresh_token:
            result["refresh_token"] = decrypt_credential(credential.refresh_token)
        
        # Add non-sensitive metadata
        if credential.extra_data:
            result.update(credential.extra_data)
        
        return result
    
    async def store_credentials(
        self,
        user_id: str,
        service: str,
        credentials: Dict[str, Any]
    ):
        """
        Store credentials for a user and service.
        
        If credentials already exist for this user/service combination,
        they will be updated.
        
        Args:
            user_id: The user's ID
            service: Service name (e.g., "google", "telegram")
            credentials: Dictionary containing credential data.
                        Must include "token" key. May include "refresh_token"
                        and other metadata.
                        
        Returns:
            The created or updated Credential instance
            
        Raises:
            ValueError: If credentials dict is missing required "token" key
        """
        # Extract and encrypt sensitive data
        extracted = self._extract_sensitive_data(credentials)
        
        async with AsyncSessionLocal() as db:
            repo = CredentialRepository(db)
            
            # Check if credential already exists
            existing = await repo.get_by_user_and_type(user_id, service)
            
            if existing:
                # Update existing credential
                return await repo.update(
                    existing.id,
                    token_value=extracted["token_value"],
                    refresh_token=extracted["refresh_token"],
                    extra_data=extracted["extra_data"]
                )
            else:
                # Create new credential
                return await repo.create(
                    user_id=user_id,
                    credential_type=service,
                    token_value=extracted["token_value"],
                    refresh_token=extracted["refresh_token"],
                    extra_data=extracted["extra_data"]
                )
    
    async def get_credentials(
        self,
        user_id: str,
        service: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a user and service.
        
        Args:
            user_id: The user's ID
            service: Service name
            
        Returns:
            Dictionary with decrypted credentials, or None if not found
        """
        async with AsyncSessionLocal() as db:
            repo = CredentialRepository(db)
            credential = await repo.get_by_user_and_type(user_id, service)
            
            if not credential:
                return None
            
            return self._reconstruct_credentials(credential)
    
    async def update_credentials(
        self,
        user_id: str,
        service: str,
        credentials: Dict[str, Any]
    ):
        """
        Update existing credentials for a user and service.
        
        Args:
            user_id: The user's ID
            service: Service name
            credentials: Dictionary containing credential data
            
        Returns:
            The updated Credential instance
            
        Raises:
            CredentialNotFoundError: If credential not found
            ValueError: If credentials dict is missing required "token" key
        """
        # Extract and encrypt sensitive data
        extracted = self._extract_sensitive_data(credentials)
        
        async with AsyncSessionLocal() as db:
            repo = CredentialRepository(db)
            
            try:
                return await repo.update_by_user_and_type(
                    user_id,
                    service,
                    token_value=extracted["token_value"],
                    refresh_token=extracted["refresh_token"],
                    extra_data=extracted["extra_data"]
                )
            except ValueError as e:
                if "not found" in str(e).lower():
                    raise CredentialNotFoundError(
                        f"Credential not found for user {user_id} and service {service}"
                    ) from e
                raise
    
    async def delete_credentials(
        self,
        user_id: str,
        service: str
    ) -> None:
        """
        Delete credentials for a user and service.
        
        Args:
            user_id: The user's ID
            service: Service name
            
        Raises:
            CredentialNotFoundError: If credential not found
        """
        async with AsyncSessionLocal() as db:
            repo = CredentialRepository(db)
            
            try:
                await repo.delete_by_user_and_type(user_id, service)
            except ValueError as e:
                if "not found" in str(e).lower():
                    raise CredentialNotFoundError(
                        f"Credential not found for user {user_id} and service {service}"
                    ) from e
                raise
