"""
Google Credential Provider Service

Provides Google OAuth credentials per-user for ADK toolsets.

Follows ADK credential patterns:
- Credentials stored in tool_context.state for runtime access
- Database used for long-term storage (refresh tokens)
- Automatic token refresh on expiration
- Integration with ADK request_credential() and get_auth_response()

Reference: ADK Authentication Documentation
https://google.github.io/adk-docs/tools-custom/authentication/
"""
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from services.credential_service import credential_service
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import ToolContext - may not be available in all ADK versions
try:
    from google.adk.tools import ToolContext
except ImportError:
    ToolContext = None


class GoogleCredentialProvider:
    """
    Provides Google OAuth credentials per-user for ADK toolsets.
    
    Follows ADK credential flow:
    1. Check tool_context.state first (runtime cache)
    2. If missing/expired, check database
    3. If expired, refresh token automatically
    4. Store in tool_context.state for future use
    """
    
    # Buffer time before expiration to refresh (5 minutes)
    REFRESH_BUFFER_SECONDS = 300
    
    def _is_valid(self, creds: Dict[str, Any]) -> bool:
        """
        Check if credentials are valid (not expired or expiring soon).
        
        Args:
            creds: Credentials dictionary
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if not creds.get("token"):
            return False
        
        # Check expiration
        expires_at = creds.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid expires_at format: {expires_at}")
                    return False
            
            if isinstance(expires_at, datetime):
                # Check if expired or expiring soon
                now = datetime.now(timezone.utc)
                buffer_time = timedelta(seconds=self.REFRESH_BUFFER_SECONDS)
                if expires_at <= (now + buffer_time):
                    return False
        
        return True
    
    def _is_expired_or_expiring_soon(self, creds: Dict[str, Any]) -> bool:
        """
        Check if credentials are expired or expiring soon.
        
        Args:
            creds: Credentials dictionary
            
        Returns:
            True if expired or expiring soon, False otherwise
        """
        return not self._is_valid(creds)
    
    async def _refresh_token(
        self,
        user_id: str,
        creds: Dict[str, Any],
        service: str = "google"
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh Google OAuth access token using refresh_token.
        
        Reference: Google OAuth2 Token Refresh
        https://developers.google.com/identity/protocols/oauth2/web-server#offline
        
        Args:
            user_id: User ID
            creds: Current credentials dictionary
            service: Service name (default: "google")
            
        Returns:
            Updated credentials dictionary or None if refresh failed
        """
        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            logger.warning(f"No refresh_token available for user {user_id}")
            return None
        
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth not configured - cannot refresh token")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                response.raise_for_status()
                tokens = response.json()
            
            # Calculate expires_at from expires_in
            expires_in = tokens.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            # Update credentials (refresh_token doesn't change)
            updated_creds = {
                "token": tokens["access_token"],
                "refresh_token": refresh_token,  # Refresh token doesn't change
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat()
            }
            
            # Preserve any existing extra_data
            if "extra_data" in creds:
                updated_creds.update(creds.get("extra_data", {}))
            
            # Store updated credentials
            await credential_service.store_credentials(
                user_id,
                service,
                updated_creds
            )
            
            logger.info(f"Successfully refreshed Google token for user {user_id}")
            return updated_creds
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                # Refresh token may be revoked - clear credentials
                logger.warning(f"Token refresh failed for user {user_id}: {e.response.status_code} - token may be revoked")
                try:
                    await credential_service.delete_credentials(user_id, service)
                except Exception as delete_error:
                    logger.error(f"Failed to delete revoked credentials: {delete_error}")
            else:
                logger.error(f"Token refresh failed for user {user_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Token refresh failed for user {user_id}: {e}", exc_info=True)
            return None
    
    def _format_for_google_api(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format credentials for Google API client.
        
        Args:
            creds: Credentials dictionary from database
            
        Returns:
            Formatted credentials dictionary
        """
        return {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "access_token": creds.get("token"),
            "refresh_token": creds.get("refresh_token"),
            "expires_at": creds.get("expires_at"),
            "expires_in": creds.get("expires_in"),
        }
    
    async def get_credentials_for_user(
        self,
        user_id: str,
        tool_context: Optional[Any] = None,
        service: str = "google"
    ) -> Optional[Dict[str, Any]]:
        """
        Get valid Google credentials for user, refreshing if needed.
        
        ADK Pattern:
        1. Check tool_context.state first (runtime cache)
        2. If missing/expired, check database
        3. If expired, refresh token automatically
        4. Store in tool_context.state for future use
        
        Args:
            user_id: User ID
            tool_context: Optional ADK ToolContext for state management
            service: Service name (default: "google")
            
        Returns:
            Formatted credentials dictionary or None if not available
        """
        cred_key = f"auth:{service}:{user_id}"
        
        # Step 1: Check tool_context.state (runtime cache)
        if tool_context and hasattr(tool_context, 'state') and tool_context.state:
            try:
                cached_creds = tool_context.state.get(cred_key)
                if cached_creds and self._is_valid(cached_creds):
                    logger.debug(f"Using cached credentials for user {user_id}")
                    return cached_creds
            except Exception as e:
                logger.debug(f"Error accessing tool_context.state: {e}")
        
        # Step 2: Check database (long-term storage)
        db_creds = await credential_service.get_credentials(user_id, service)
        if not db_creds:
            logger.debug(f"No credentials found in database for user {user_id}, service {service}")
            return None
        
        # Step 3: Check expiration and refresh if needed
        if self._is_expired_or_expiring_soon(db_creds):
            logger.debug(f"Credentials expired or expiring soon for user {user_id}, refreshing...")
            db_creds = await self._refresh_token(user_id, db_creds, service)
            if not db_creds:
                logger.warning(f"Failed to refresh credentials for user {user_id}")
                return None
        
        # Step 4: Format for Google API and cache in tool_context.state
        formatted_creds = self._format_for_google_api(db_creds)
        
        if tool_context and hasattr(tool_context, 'state') and tool_context.state:
            try:
                tool_context.state[cred_key] = formatted_creds
                logger.debug(f"Cached credentials in tool_context.state for user {user_id}")
            except Exception as e:
                logger.debug(f"Error caching credentials in tool_context.state: {e}")
        
        return formatted_creds


# Global singleton instance
_google_credential_provider: Optional[GoogleCredentialProvider] = None


def get_google_credential_provider() -> GoogleCredentialProvider:
    """Get singleton GoogleCredentialProvider instance."""
    global _google_credential_provider
    if _google_credential_provider is None:
        _google_credential_provider = GoogleCredentialProvider()
    return _google_credential_provider
