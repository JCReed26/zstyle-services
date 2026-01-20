"""
Supabase User Service

Provides user management operations using Supabase Python SDK.
Handles user lookups, creation, and profile management using Supabase's built-in features.

Uses Supabase SDK for Auth operations and SQLAlchemy for profile data operations.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from supabase import Client
from app.supabase_client import get_supabase_client
from app.config import settings
from database.availability import is_database_available
from database.engine import AsyncSessionLocal
from database.repositories import UserRepository

logger = logging.getLogger(__name__)


class SupabaseUserService:
    """
    Service for user operations using Supabase Python SDK.
    
    Uses Supabase client for Auth operations and SQLAlchemy
    for profile data operations. Leverages Supabase SDK built-in features
    to avoid code duplication.
    """
    
    def __init__(self):
        """Initialize service with Supabase clients (lazy initialization)."""
        self._supabase: Optional[Client] = None
        self._supabase_admin: Optional[Client] = None
    
    @property
    def supabase(self) -> Optional[Client]:
        """
        Get Supabase client (anon key, respects RLS).
        
        Uses lazy initialization to match existing pattern.
        """
        if not settings.has_database():
            return None
        
        if self._supabase is None:
            try:
                self._supabase = get_supabase_client(use_service_role=False)
            except Exception as e:
                logger.error(f"Failed to create Supabase client: {e}", exc_info=True)
                return None
        return self._supabase
    
    @property
    def supabase_admin(self) -> Optional[Client]:
        """
        Get Supabase admin client (service role key, bypasses RLS).
        
        Uses lazy initialization to match existing pattern.
        """
        if not settings.has_database():
            return None
        
        if self._supabase_admin is None:
            try:
                self._supabase_admin = get_supabase_client(use_service_role=True)
            except Exception as e:
                logger.error(f"Failed to create Supabase admin client: {e}", exc_info=True)
                return None
        return self._supabase_admin
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by Telegram ID using database query.
        
        Uses SQLAlchemy repository pattern for profile data.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User dictionary or None if not found
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot lookup user by Telegram ID {telegram_id}")
            return None
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_telegram_id(telegram_id)
                
                if user:
                    return {
                        "id": str(user.id),
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "is_active": user.is_active
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving user by Telegram ID {telegram_id}: {e}", exc_info=True)
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID (auth.users.id) using database query.
        
        Uses SQLAlchemy repository pattern for profile data.
        
        Args:
            user_id: UUID from auth.users.id
            
        Returns:
            User dictionary or None if not found
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot lookup user {user_id}")
            return None
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_id(user_id)
                
                if user:
                    return {
                        "id": str(user.id),
                        "telegram_id": user.telegram_id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "is_active": user.is_active
                    }
                return None
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}", exc_info=True)
            return None
    
    async def create_user(
        self,
        user_id: str,
        telegram_id: Optional[int] = None,
        username: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new user profile.
        
        Note: User must already exist in auth.users. This creates the profile.
        Uses SQLAlchemy repository pattern for profile data.
        
        Args:
            user_id: UUID from auth.users.id (required)
            telegram_id: Optional Telegram ID
            username: Optional username
            display_name: Optional display name
            
        Returns:
            Created user dictionary or None if creation failed
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot create user {user_id}")
            return None
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.create(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    username=username,
                    display_name=display_name
                )
                
                return {
                    "id": str(user.id),
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "is_active": user.is_active
                }
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}", exc_info=True)
            return None
    
    async def get_user_embeddings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user vector embeddings for semantic search.
        
        TODO: Implement vector embedding retrieval from Supabase.
        This should use Supabase's vector extension (pgvector) or Supabase SDK
        vector search capabilities.
        
        Args:
            user_id: UUID from auth.users.id
            
        Returns:
            Dictionary with embeddings or None if not found
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot retrieve embeddings for user {user_id}")
            return None
        
        # TODO: Implement vector embedding retrieval
        # Example approach:
        # 1. Use Supabase SDK to query vector columns
        # 2. Or use SQLAlchemy with pgvector extension
        # 3. Return embeddings in a standardized format
        logger.warning("get_user_embeddings not yet implemented")
        return None


# Global singleton instance
supabase_user_service = SupabaseUserService()
