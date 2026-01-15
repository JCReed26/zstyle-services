"""
Credential Repository

Repository pattern for Credential model operations.
Provides abstraction layer for credential data access.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any

from core.database.models import Credential


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
        user_id: str, 
        credential_type: str
    ) -> Optional[Credential]:
        """
        Retrieve a credential by user ID and credential type.
        
        Args:
            user_id: The user's ID
            credential_type: The type of credential (e.g., "google", "telegram")
            
        Returns:
            Credential instance if found, None otherwise
        """
        result = await self.session.execute(
            select(Credential).where(
                Credential.user_id == user_id,
                Credential.credential_type == credential_type
            )
        )
        return result.scalar_one_or_none()
    
    async def create(
        self,
        user_id: str,
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
            user_id: The user's ID
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
        credential_id: str,
        **kwargs
    ) -> Credential:
        """
        Update an existing credential.
        
        Args:
            credential_id: The credential's ID
            **kwargs: Credential attributes to update
            
        Returns:
            The updated Credential instance
            
        Raises:
            ValueError: If credential not found
        """
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
        user_id: str,
        credential_type: str,
        **kwargs
    ) -> Credential:
        """
        Update a credential by user ID and credential type.
        
        Args:
            user_id: The user's ID
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
    
    async def delete(self, credential_id: str) -> None:
        """
        Delete a credential (hard delete).
        
        Args:
            credential_id: The credential's ID
            
        Raises:
            ValueError: If credential not found
        """
        credential = await self.session.get(Credential, credential_id)
        if not credential:
            raise ValueError(f"Credential not found: {credential_id}")
        
        await self.session.delete(credential)
        await self.session.commit()
    
    async def delete_by_user_and_type(
        self,
        user_id: str,
        credential_type: str
    ) -> None:
        """
        Delete a credential by user ID and credential type.
        
        Args:
            user_id: The user's ID
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
    
    async def get_all_by_user(self, user_id: str) -> List[Credential]:
        """
        Get all credentials for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of Credential instances
        """
        result = await self.session.execute(
            select(Credential).where(Credential.user_id == user_id)
        )
        return list(result.scalars().all())
