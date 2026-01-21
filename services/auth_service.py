"""
Authentication Service

Handles user authentication using phone number as primary identifier.
Relies on Telegram's contact verification - no OTP required.

Supports graceful degradation - returns None/empty results if database unavailable.
"""
import logging
import uuid
from typing import Optional, Dict, Any

from app.config import settings
from database.engine import AsyncSessionLocal
from database.repositories import UserRepository
from database.availability import is_database_available

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for handling authentication with phone number.
    
    Creates users directly when phone number is shared via Telegram.
    Relies on Telegram's built-in contact verification.
    """
    
    def __init__(self):
        """Initialize auth service."""
        pass
    
    async def create_user_with_phone(
        self,
        phone_number: str,
        telegram_id: int,
        telegram_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create user account directly from phone number and Telegram ID.
        No OTP verification - relies on Telegram's contact verification.
        
        Args:
            phone_number: Phone number in E.164 format
            telegram_id: Telegram user ID
            telegram_username: Optional Telegram username
        
        Returns:
            Dictionary with user_id
        
        Raises:
            RuntimeError: If database is not available
            ValueError: If user creation fails
        """
        if not is_database_available():
            raise RuntimeError("Database is not available - cannot create user")
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                
                # Check if user already exists by telegram_id
                existing_user = await repo.get_by_telegram_id(telegram_id)
                if existing_user:
                    logger.info(f"User already exists: {existing_user.id}")
                    return {
                        "success": True,
                        "user_id": str(existing_user.id),
                        "phone_number": phone_number
                    }
                
                # Generate user ID (UUID)
                user_id = uuid.uuid4()
                
                # Create user profile with phone and telegram info
                user = await repo.create(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    username=telegram_username,
                    display_name=None,
                    other_ids={"phone_number": phone_number}
                )
                
                logger.info(f"Created user {user_id} for phone {phone_number[:5]}****")
                
                return {
                    "success": True,
                    "user_id": str(user_id),
                    "phone_number": phone_number
                }
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            raise ValueError(f"Failed to create user account: {str(e)}")
    
    async def get_user_by_auth_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by user ID.
        
        Args:
            user_id: UUID from auth.users.id
        
        Returns:
            User dictionary or None if not found or database unavailable
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot retrieve user {user_id}")
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
    
    async def link_telegram_id(
        self, 
        user_id: str, 
        telegram_id: int,
        telegram_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Link Telegram ID to user account.
        
        Args:
            user_id: UUID from auth.users.id
            telegram_id: Telegram user ID
            telegram_username: Optional Telegram username
        
        Returns:
            Updated user information
        
        Raises:
            RuntimeError: If database is not available
            ValueError: If user not found
        """
        if not is_database_available():
            raise RuntimeError("Database is not available - cannot link Telegram ID")
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_id(user_id)
                
                if not user:
                    raise ValueError(f"User not found: {user_id}")
                
                # Update Telegram ID and username
                update_data = {"telegram_id": telegram_id}
                if telegram_username:
                    update_data["username"] = telegram_username
                
                user = await repo.update(user.id, **update_data)
                
                logger.info(f"Linked Telegram ID {telegram_id} to user {user.id}")
                
                return {
                    "id": str(user.id),
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "display_name": user.display_name
                }
        except (RuntimeError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Error linking Telegram ID: {e}", exc_info=True)
            raise
    


# Global singleton instance
auth_service = AuthService()
