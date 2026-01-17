"""
Authentication Service

Handles user authentication using Supabase Auth with phone number as primary identifier.
Phone numbers are stored in auth.users.phone, not in the custom users table.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from app.supabase_client import get_supabase_client
from database.engine import AsyncSessionLocal
from database.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for handling authentication with Supabase Auth.
    
    Uses phone number as primary identifier, which works seamlessly with Telegram.
    Phone numbers are stored in auth.users.phone. The users table stores profile data
    and is automatically created via trigger when auth.users is created.
    """
    
    def __init__(self):
        """Initialize auth service with Supabase client (lazy initialization)."""
        self._supabase = None
        self._supabase_admin = None
    
    @property
    def supabase(self):
        """Get Supabase client (lazy initialization)."""
        if self._supabase is None:
            self._supabase = get_supabase_client()
        return self._supabase
    
    @property
    def supabase_admin(self):
        """Get Supabase admin client (lazy initialization)."""
        if self._supabase_admin is None:
            self._supabase_admin = get_supabase_client(use_service_role=True)
        return self._supabase_admin
    
    async def initiate_phone_auth(self, phone_number: str) -> Dict[str, Any]:
        """
        Initiate phone number authentication by sending OTP.
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +1234567890)
        
        Returns:
            Dictionary with status and message
        
        Raises:
            ValueError: If Supabase is not configured
        """
        if not self.supabase:
            raise ValueError("Supabase Auth is not configured")
        
        try:
            # Send OTP via Supabase Auth
            response = self.supabase.auth.sign_in_with_otp({
                "phone": phone_number
            })
            
            logger.info(f"OTP sent to phone number: {phone_number[:5]}****")
            
            return {
                "success": True,
                "message": "OTP sent successfully",
                "phone": phone_number  # Return for verification
            }
        except Exception as e:
            logger.error(f"Failed to send OTP: {e}", exc_info=True)
            raise ValueError(f"Failed to send OTP: {str(e)}")
    
    async def verify_phone_auth(
        self, 
        phone_number: str, 
        token: str
    ) -> Dict[str, Any]:
        """
        Verify OTP token and create/update user session.
        
        The user profile in public.users is automatically created via trigger
        when auth.users is created by Supabase Auth.
        
        Args:
            phone_number: Phone number in E.164 format
            token: OTP token received via SMS
        
        Returns:
            Dictionary with access_token, user info, and user_id (UUID)
        
        Raises:
            ValueError: If verification fails
        """
        try:
            # Verify OTP with Supabase Auth
            response = self.supabase.auth.verify_otp({
                "phone": phone_number,
                "token": token,
                "type": "sms"
            })
            
            if not response.session:
                raise ValueError("OTP verification failed - no session created")
            
            # Get user ID from Supabase Auth response
            user_id = response.user.id  # This is UUID from auth.users
            access_token = response.session.access_token
            refresh_token = response.session.refresh_token
            
            # Profile should be auto-created by trigger, but verify it exists
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_id(user_id)
                
                if not user:
                    # Trigger may not have fired yet, create profile explicitly
                    logger.warning(f"Profile not found for user {user_id}, creating explicitly")
                    user = await repo.create(user_id=user_id)
                    logger.info(f"Created profile for user {user_id}")
                else:
                    logger.debug(f"Profile exists for user {user_id}")
            
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_id": str(user_id),  # Return as string for JSON serialization
                "phone_number": phone_number
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"OTP verification failed: {e}", exc_info=True)
            raise ValueError(f"OTP verification failed: {str(e)}")
    
    async def get_user_by_auth_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by Supabase Auth user ID.
        
        Args:
            user_id: UUID from auth.users.id
        
        Returns:
            User dictionary or None if not found
        """
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
            ValueError: If user not found
        """
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
    
    async def get_user_by_phone_from_supabase(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user information by phone number using Supabase Auth.
        
        This queries Supabase Auth directly, not the custom users table.
        
        Args:
            phone_number: Phone number in E.164 format
        
        Returns:
            User dictionary with auth.users data, or None if not found
        """
        try:
            # Use admin client to query auth.users
            # Note: This requires service role key
            admin_client = self.supabase_admin
            
            # Supabase doesn't have a direct "get user by phone" API
            # We'd need to use the admin API or store phone->user_id mapping
            # For now, return None - this method may not be needed
            logger.warning("get_user_by_phone_from_supabase not fully implemented - use get_user_by_auth_id instead")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by phone: {e}", exc_info=True)
            return None


# Global singleton instance
auth_service = AuthService()
