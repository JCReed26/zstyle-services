"""
Database Repositories

Repository pattern for database operations. All repositories consolidated in one file.
Provides abstraction layer for database access.

Usage:
    from database.repositories import UserRepository, CredentialRepository, OAuthStateRepository
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone, timedelta

from database.models import User, Credential, OAuthState


class UserRepository:
    """
    Repository for User model operations.
    
    Provides standard CRUD operations and common queries.
    All database operations for User should go through this repository.
    
    Note: User.id is a UUID that references auth.users(id).
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_by_id(self, user_id: Union[UUID, str]) -> Optional[User]:
        """
        Retrieve a user by their ID (auth.users.id).
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            
        Returns:
            User instance if found, None otherwise
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
            
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_auth_uid(self, auth_uid: Union[UUID, str]) -> Optional[User]:
        """
        Retrieve a user by their Supabase Auth user ID.
        
        This is an alias for get_by_id since id directly references auth.users(id).
        
        Args:
            auth_uid: The user's Supabase Auth UUID
            
        Returns:
            User instance if found, None otherwise
        """
        return await self.get_by_id(auth_uid)
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Retrieve a user by their Telegram ID.
        
        Args:
            telegram_id: The user's Telegram ID
            
        Returns:
            User instance if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, user_id: Union[UUID, str], **kwargs) -> User:
        """
        Create a new user profile.
        
        Note: The user must already exist in auth.users. This creates the profile.
        The trigger should handle this automatically, but this method allows
        explicit profile creation if needed.
        
        Args:
            user_id: The UUID from auth.users.id (required)
            **kwargs: User attributes (telegram_id, username, display_name, etc.)
            
        Returns:
            The created User instance
            
        Raises:
            IntegrityError: If unique constraint violated (e.g., duplicate telegram_id)
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # Ensure id is set
        kwargs['id'] = user_id
        
        user = User(**kwargs)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(self, user_id: Union[UUID, str], **kwargs) -> User:
        """
        Update an existing user.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            **kwargs: User attributes to update (telegram_id, username, display_name, etc.)
            
        Returns:
            The updated User instance
            
        Raises:
            ValueError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Update attributes (exclude id and other protected fields)
        protected_fields = {'id', 'created_at'}
        for key, value in kwargs.items():
            if key not in protected_fields and hasattr(user, key):
                setattr(user, key, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user_id: Union[UUID, str]) -> None:
        """
        Delete a user profile (hard delete).
        
        Note: This will cascade delete related records due to foreign key constraints.
        The auth.users record should be deleted via Supabase Auth.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            
        Raises:
            ValueError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        await self.session.delete(user)
        await self.session.commit()


class CredentialRepository:
    """
    Repository for Credential model operations.
    
    Provides standard CRUD operations and common queries.
    All database operations for Credential should go through this repository.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_by_user_and_type(
        self, 
        user_id: Union[UUID, str], 
        credential_type: str
    ) -> Optional[Credential]:
        """
        Retrieve a credential by user ID and credential type.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            credential_type: The type of credential (e.g., "google_oauth", "ticktick_token")
            
        Returns:
            Credential instance if found, None otherwise
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
            
        result = await self.session.execute(
            select(Credential).where(
                Credential.user_id == user_id,
                Credential.credential_type == credential_type
            )
        )
        return result.scalar_one_or_none()
    
    async def create(
        self,
        user_id: Union[UUID, str],
        credential_type: str,
        token_value: str,
        refresh_token: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[Any] = None,
        is_active: bool = True
    ) -> Credential:
        """
        Create a new credential.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            credential_type: The type of credential
            token_value: Encrypted token value
            refresh_token: Optional encrypted refresh token
            extra_data: Optional metadata dictionary
            expires_at: Optional expiration datetime
            is_active: Whether credential is active
            
        Returns:
            The created Credential instance
            
        Raises:
            IntegrityError: If unique constraint violated
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
            
        credential = Credential(
            user_id=user_id,
            credential_type=credential_type,
            token_value=token_value,
            refresh_token=refresh_token,
            extra_data=extra_data or {},
            expires_at=expires_at,
            is_active=is_active
        )
        self.session.add(credential)
        await self.session.commit()
        await self.session.refresh(credential)
        return credential
    
    async def update(
        self,
        credential_id: Union[UUID, str],
        **kwargs
    ) -> Credential:
        """
        Update an existing credential.
        
        Args:
            credential_id: The credential's UUID
            **kwargs: Credential attributes to update
            
        Returns:
            The updated Credential instance
            
        Raises:
            ValueError: If credential not found
        """
        # Convert string to UUID if needed
        if isinstance(credential_id, str):
            credential_id = UUID(credential_id)
            
        credential = await self.session.get(Credential, credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        # Update attributes
        for key, value in kwargs.items():
            if hasattr(credential, key):
                setattr(credential, key, value)
        
        await self.session.commit()
        await self.session.refresh(credential)
        return credential
    
    async def update_by_user_and_type(
        self,
        user_id: Union[UUID, str],
        credential_type: str,
        **kwargs
    ) -> Credential:
        """
        Update a credential by user ID and credential type.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            credential_type: The type of credential
            **kwargs: Credential attributes to update
            
        Returns:
            The updated Credential instance
            
        Raises:
            ValueError: If credential not found
        """
        credential = await self.get_by_user_and_type(user_id, credential_type)
        if not credential:
            raise ValueError(
                f"Credential not found for user {user_id} and type {credential_type}"
            )
        
        return await self.update(credential.id, **kwargs)
    
    async def delete(self, credential_id: Union[UUID, str]) -> None:
        """
        Delete a credential (hard delete).
        
        Args:
            credential_id: The credential's UUID
            
        Raises:
            ValueError: If credential not found
        """
        # Convert string to UUID if needed
        if isinstance(credential_id, str):
            credential_id = UUID(credential_id)
            
        credential = await self.session.get(Credential, credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        await self.session.delete(credential)
        await self.session.commit()
    
    async def delete_by_user_and_type(
        self,
        user_id: Union[UUID, str],
        credential_type: str
    ) -> None:
        """
        Delete a credential by user ID and credential type.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            credential_type: The type of credential
            
        Raises:
            ValueError: If credential not found
        """
        credential = await self.get_by_user_and_type(user_id, credential_type)
        if not credential:
            raise ValueError(
                f"Credential not found for user {user_id} and type {credential_type}"
            )
        
        await self.delete(credential.id)
    
    async def get_all_by_user(self, user_id: Union[UUID, str]) -> List[Credential]:
        """
        Get all credentials for a user.
        
        Args:
            user_id: The user's UUID (from auth.users.id)
            
        Returns:
            List of Credential instances
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
            
        result = await self.session.execute(
            select(Credential).where(Credential.user_id == user_id)
        )
        return list(result.scalars().all())


class OAuthStateRepository:
    """
    Repository for OAuthState model operations.
    
    Handles CRUD operations for OAuth state tokens used in OAuth flows.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def create(
        self,
        state_token: str,
        user_id: Union[UUID, str],
        service: str,
        expiration_minutes: int = 10
    ) -> OAuthState:
        """
        Create a new OAuth state token.
        
        Args:
            state_token: Cryptographically random state token
            user_id: User UUID (from auth.users.id) associated with this OAuth flow
            service: Service name (e.g., "google", "ticktick")
            expiration_minutes: Minutes until state expires (default: 10)
            
        Returns:
            Created OAuthState instance
        """
        # Convert string to UUID if needed
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
        
        oauth_state = OAuthState(
            state_token=state_token,
            user_id=user_id,
            service=service,
            expires_at=expires_at,
            consumed=False
        )
        
        self.session.add(oauth_state)
        await self.session.commit()
        await self.session.refresh(oauth_state)
        return oauth_state
    
    async def get_by_token(
        self,
        state_token: str
    ) -> Optional[OAuthState]:
        """
        Retrieve OAuth state by token.
        
        Args:
            state_token: State token to lookup
            
        Returns:
            OAuthState instance if found and valid, None otherwise
        """
        result = await self.session.execute(
            select(OAuthState).where(
                and_(
                    OAuthState.state_token == state_token,
                    OAuthState.consumed == False,
                    OAuthState.expires_at > datetime.now(timezone.utc)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def consume_token(
        self,
        state_token: str
    ) -> Optional[OAuthState]:
        """
        Mark a state token as consumed (single-use).
        
        Args:
            state_token: State token to consume
            
        Returns:
            OAuthState instance if found and valid, None otherwise
            
        Raises:
            ValueError: If token already consumed or expired
        """
        oauth_state = await self.get_by_token(state_token)
        
        if not oauth_state:
            return None
        
        if oauth_state.consumed:
            raise ValueError("State token already consumed")
        
        if oauth_state.is_expired():
            raise ValueError("State token expired")
        
        oauth_state.consumed = True
        await self.session.commit()
        await self.session.refresh(oauth_state)
        return oauth_state
    
    async def cleanup_expired(self) -> int:
        """
        Delete expired OAuth states.
        
        Returns:
            Number of states deleted
        """
        result = await self.session.execute(
            delete(OAuthState).where(
                OAuthState.expires_at < datetime.now(timezone.utc)
            )
        )
        await self.session.commit()
        return result.rowcount


__all__ = [
    "UserRepository",
    "CredentialRepository",
    "OAuthStateRepository",
]
