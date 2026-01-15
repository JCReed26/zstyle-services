"""
User Repository

Repository pattern for User model operations.
Provides abstraction layer for user data access.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from core.database.models import User


class UserRepository:
    """
    Repository for User model operations.
    
    Provides standard CRUD operations and common queries.
    All database operations for User should go through this repository.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by their internal ID.
        
        Args:
            user_id: The user's internal ID
            
        Returns:
            User instance if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
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
    
    async def create(self, **kwargs) -> User:
        """
        Create a new user.
        
        Args:
            **kwargs: User attributes (telegram_id, username, email, etc.)
            
        Returns:
            The created User instance
            
        Raises:
            IntegrityError: If unique constraint violated (e.g., duplicate telegram_id)
        """
        user = User(**kwargs)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(self, user_id: str, **kwargs) -> User:
        """
        Update an existing user.
        
        Args:
            user_id: The user's internal ID
            **kwargs: User attributes to update
            
        Returns:
            The updated User instance
            
        Raises:
            ValueError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # Update attributes
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user_id: str) -> None:
        """
        Delete a user (hard delete).
        
        Args:
            user_id: The user's internal ID
            
        Raises:
            ValueError: If user not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        await self.session.delete(user)
        await self.session.commit()
