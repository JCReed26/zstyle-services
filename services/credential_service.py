"""
Credential Service

Provides secure storage and retrieval of user credentials.
Encrypts sensitive tokens while storing non-sensitive metadata unencrypted.

Supports graceful degradation - returns None if database unavailable.

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
        "scope": "read write",
        "expires_in": 3600  # Will automatically calculate expires_at
    }
)

# Retrieve credentials
creds = await credential_service.get_credentials(
    user_id="user123",
    service="google"
)
"""
import logging
import asyncio
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from database.engine import AsyncSessionLocal
from database.repositories import CredentialRepository
from database.availability import is_database_available
from app.security import encrypt_credential, decrypt_credential

logger = logging.getLogger(__name__)


class CredentialNotFoundError(Exception):
    """Raised when a credential is not found."""
    pass


class CredentialService:
    """
    Service for managing user credentials securely.
    
    Handles encryption/decryption of sensitive tokens and storage
    of non-sensitive metadata. All sensitive data (tokens, API keys)
    are encrypted at rest.
    
    Includes in-memory caching for faster credential retrieval during
    active user sessions. Cache is automatically invalidated on updates.
    """
    
    # Sensitive keys that should be encrypted
    SENSITIVE_KEYS = {"token", "refresh_token", "api_key", "secret", "password"}
    
    # Cache configuration
    _cache: Dict[Tuple[str, str], Tuple[Dict[str, Any], float]] = {}
    _cache_lock: asyncio.Lock = asyncio.Lock()
    _cache_ttl: int = 300  # 5 minutes cache TTL
    
    def _get_cache_key(self, user_id: str, service: str) -> Tuple[str, str]:
        """Generate cache key from user_id and service."""
        return (str(user_id), str(service))
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid based on TTL."""
        return time.time() - timestamp < self._cache_ttl
    
    async def _get_from_cache(self, cache_key: Tuple[str, str]) -> Optional[Dict[str, Any]]:
        """Get credentials from cache if valid."""
        async with self._cache_lock:
            if cache_key in self._cache:
                creds, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    logger.debug(f"Cache hit for {cache_key[0]}/{cache_key[1]}")
                    return creds
                else:
                    # Cache expired, remove it
                    del self._cache[cache_key]
                    logger.debug(f"Cache expired for {cache_key[0]}/{cache_key[1]}")
        return None
    
    async def _set_cache(self, cache_key: Tuple[str, str], credentials: Dict[str, Any]) -> None:
        """Store credentials in cache."""
        async with self._cache_lock:
            self._cache[cache_key] = (credentials, time.time())
            logger.debug(f"Cached credentials for {cache_key[0]}/{cache_key[1]}")
    
    async def _invalidate_cache(self, cache_key: Tuple[str, str]) -> None:
        """Remove credentials from cache."""
        async with self._cache_lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug(f"Cache invalidated for {cache_key[0]}/{cache_key[1]}")
    
    def _get_session_context(self, session: Optional[AsyncSession] = None):
        """
        Get a database session context manager.
        
        Args:
            session: Optional existing session to use. If None, creates a new session.
            
        Returns:
            Context manager that yields an AsyncSession
        """
        if session is not None:
            # Use provided session (don't close it) - create a no-op context manager
            @asynccontextmanager
            async def _noop_context():
                yield session
            return _noop_context()
        else:
            # Create new session
            return AsyncSessionLocal()
    
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
            Dictionary with decrypted tokens and metadata, including expires_at
        """
        result = {}
        
        # Decrypt token
        if credential.token_value:
            result["token"] = decrypt_credential(credential.token_value)
        
        # Decrypt refresh_token if present
        if credential.refresh_token:
            result["refresh_token"] = decrypt_credential(credential.refresh_token)
        
        # Add expiration information
        if credential.expires_at:
            result["expires_at"] = credential.expires_at.isoformat()
            # Calculate expires_in for convenience
            now = datetime.now(timezone.utc)
            if credential.expires_at > now:
                expires_in = int((credential.expires_at - now).total_seconds())
                result["expires_in"] = expires_in
        
        # Add non-sensitive metadata
        if credential.extra_data:
            result.update(credential.extra_data)
        
        return result
    
    def _calculate_expires_at(self, credentials: Dict[str, Any]) -> Optional[datetime]:
        """
        Calculate expires_at from expires_in if provided.
        
        Args:
            credentials: Dictionary containing credential data
            
        Returns:
            datetime object for expires_at, or None if expires_in not provided
        """
        # Check if expires_at is already provided
        if "expires_at" in credentials:
            expires_at = credentials["expires_at"]
            if isinstance(expires_at, str):
                # Parse ISO format string
                try:
                    return datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid expires_at format: {expires_at}")
            elif isinstance(expires_at, datetime):
                return expires_at
            return None
        
        # Calculate from expires_in
        if "expires_in" in credentials:
            expires_in = credentials.get("expires_in")
            if expires_in:
                try:
                    expires_in_seconds = int(expires_in)
                    return datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid expires_in value: {expires_in}")
        
        return None
    
    async def store_credentials(
        self,
        user_id: str,
        service: str,
        credentials: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ):
        """
        Store credentials for a user and service.
        
        If credentials already exist for this user/service combination,
        they will be updated. Cache is automatically invalidated and updated.
        
        Enhancement: Automatically calculates expires_at from expires_in if provided.
        
        Args:
            user_id: The user's ID
            service: Service name (e.g., "google", "telegram")
            credentials: Dictionary containing credential data.
                        Must include "token" key. May include "refresh_token",
                        "expires_in" (seconds), "expires_at" (datetime), and other metadata.
            session: Optional database session to use. If None, creates a new session.
                        
        Returns:
            The created or updated Credential instance, or None if database unavailable
            
        Raises:
            RuntimeError: If database is not available
            ValueError: If credentials dict is missing required "token" key
        """
        cache_key = self._get_cache_key(user_id, service)
        
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot store credentials for user {user_id}, service {service}")
            raise RuntimeError("Database is not available - cannot store credentials")
        
        try:
            # Calculate expires_at from expires_in if provided
            expires_at = self._calculate_expires_at(credentials)
            
            # Extract and encrypt sensitive data
            extracted = self._extract_sensitive_data(credentials)
            
            async with self._get_session_context(session) as db:
                repo = CredentialRepository(db)
                
                # Check if credential already exists
                existing = await repo.get_by_user_and_type(user_id, service)
                
                if existing:
                    # Update existing credential
                    updated_credential = await repo.update(
                        existing.id,
                        token_value=extracted["token_value"],
                        refresh_token=extracted["refresh_token"],
                        extra_data=extracted["extra_data"],
                        expires_at=expires_at
                    )
                else:
                    # Create new credential
                    updated_credential = await repo.create(
                        user_id=user_id,
                        credential_type=service,
                        token_value=extracted["token_value"],
                        refresh_token=extracted["refresh_token"],
                        extra_data=extracted["extra_data"],
                        expires_at=expires_at
                    )
                
                # Update cache with new credentials immediately
                reconstructed_creds = self._reconstruct_credentials(updated_credential)
                await self._set_cache(cache_key, reconstructed_creds)
                
                return updated_credential
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}", exc_info=True)
            # Invalidate cache on error
            await self._invalidate_cache(cache_key)
            raise
    
    async def get_credentials(
        self,
        user_id: str,
        service: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a user and service.
        
        Uses in-memory cache for faster access during active sessions.
        Cache is automatically invalidated on credential updates.
        
        SECURITY: Validates user_id matches credential owner.
        
        Args:
            user_id: The user's ID
            service: Service name
            session: Optional database session to use. If None, creates a new session.
            
        Returns:
            Dictionary with decrypted credentials, or None if not found or database unavailable
        """
        cache_key = self._get_cache_key(user_id, service)
        
        # Check cache first
        cached_creds = await self._get_from_cache(cache_key)
        if cached_creds is not None:
            return cached_creds
        
        # Cache miss - query database
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot retrieve credentials for user {user_id}, service {service}")
            return None
        
        try:
            async with self._get_session_context(session) as db:
                repo = CredentialRepository(db)
                credential = await repo.get_by_user_and_type(user_id, service)
                
                if not credential:
                    return None
                
                # SECURITY: Verify user_id matches
                if str(credential.user_id) != str(user_id):
                    logger.error(f"CRITICAL: User ID mismatch for credential access")
                    return None
                
                creds = self._reconstruct_credentials(credential)
                
                # Cache the result for faster future access
                await self._set_cache(cache_key, creds)
                
                return creds
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}", exc_info=True)
            return None
    
    async def update_credentials(
        self,
        user_id: str,
        service: str,
        credentials: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ):
        """
        Update existing credentials for a user and service.
        
        Cache is automatically invalidated and updated with new credentials.
        
        Args:
            user_id: The user's ID
            service: Service name
            credentials: Dictionary containing credential data
            session: Optional database session to use. If None, creates a new session.
            
        Returns:
            The updated Credential instance
            
        Raises:
            CredentialNotFoundError: If credential not found
            ValueError: If credentials dict is missing required "token" key
        """
        cache_key = self._get_cache_key(user_id, service)
        
        # Extract and encrypt sensitive data
        extracted = self._extract_sensitive_data(credentials)
        
        async with self._get_session_context(session) as db:
            repo = CredentialRepository(db)
            
            try:
                updated_credential = await repo.update_by_user_and_type(
                    user_id,
                    service,
                    token_value=extracted["token_value"],
                    refresh_token=extracted["refresh_token"],
                    extra_data=extracted["extra_data"]
                )
                
                # Update cache with new credentials
                reconstructed_creds = self._reconstruct_credentials(updated_credential)
                await self._set_cache(cache_key, reconstructed_creds)
                
                return updated_credential
            except ValueError as e:
                if "not found" in str(e).lower():
                    # Invalidate cache if credential not found
                    await self._invalidate_cache(cache_key)
                    raise CredentialNotFoundError(
                        f"Credential not found for user {user_id} and service {service}"
                    ) from e
                raise
    
    async def delete_credentials(
        self,
        user_id: str,
        service: str,
        session: Optional[AsyncSession] = None
    ) -> None:
        """
        Delete credentials for a user and service.
        
        Cache is automatically invalidated on deletion.
        
        Args:
            user_id: The user's ID
            service: Service name
            session: Optional database session to use. If None, creates a new session.
            
        Raises:
            CredentialNotFoundError: If credential not found
        """
        cache_key = self._get_cache_key(user_id, service)
        
        async with self._get_session_context(session) as db:
            repo = CredentialRepository(db)
            
            try:
                await repo.delete_by_user_and_type(user_id, service)
                # Invalidate cache after successful deletion
                await self._invalidate_cache(cache_key)
            except ValueError as e:
                if "not found" in str(e).lower():
                    # Invalidate cache even if not found (cleanup)
                    await self._invalidate_cache(cache_key)
                    raise CredentialNotFoundError(
                        f"Credential not found for user {user_id} and service {service}"
                    ) from e
                raise


            
credential_service = CredentialService()