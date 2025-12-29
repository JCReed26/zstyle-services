"""
OAuth Service

Handles OAuth flows for external services.
Only Google OAuth for now (TickTick uses hardcoded token).
"""
import os
import secrets
import requests
import urllib.parse
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone

from services.auth.auth_service import auth_service

logger = logging.getLogger(__name__)

# OAuth state storage for CSRF protection
# Format: {state: (user_id, expires_at)}
_oauth_states: Dict[str, Tuple[str, datetime]] = {}


def _cleanup_expired_oauth_states():
    """Remove expired OAuth states from storage."""
    global _oauth_states
    now = datetime.utcnow()
    expired = [state for state, (_, expires_at) in _oauth_states.items() if now > expires_at]
    for state in expired:
        del _oauth_states[state]


class OAuthService:
    """
    Service for handling OAuth flows.
    
    Supports Google OAuth and TickTick OAuth.
    """
    
    @staticmethod
    def get_google_auth_url(user_id: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            user_id: User ID to associate with this OAuth flow
            
        Returns:
            Authorization URL string
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            # Try to construct from Cloud Run URL
            cloud_run_url = os.getenv("CLOUD_RUN_URL")
            if cloud_run_url:
                redirect_uri = f"{cloud_run_url}/api/oauth/google/callback"
            else:
                # Fallback to localhost for development
                redirect_uri = "http://localhost:8000/api/oauth/google/callback"
        
        if not client_id:
            raise ValueError("GOOGLE_CLIENT_ID not configured")
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Clean up expired states
        _cleanup_expired_oauth_states()
        
        # Store state -> user_id mapping (10 min TTL)
        _oauth_states[state] = (user_id, datetime.utcnow() + timedelta(minutes=10))
        
        # Google OAuth scopes
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events"
        ]
        scope_string = " ".join(scopes)
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    async def handle_google_callback(code: str, state: str) -> Tuple[bool, Optional[str]]:
        """
        Handle Google OAuth callback.
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Validate state
        if state not in _oauth_states:
            return False, "Invalid or expired state parameter"
        
        user_id, expires_at = _oauth_states[state]
        
        if datetime.utcnow() > expires_at:
            del _oauth_states[state]
            return False, "State parameter expired"
        
        # Clean up used state
        del _oauth_states[state]
        
        # Exchange code for tokens
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        if not redirect_uri:
            # Try to construct from Cloud Run URL
            cloud_run_url = os.getenv("CLOUD_RUN_URL")
            if cloud_run_url:
                redirect_uri = f"{cloud_run_url}/api/oauth/google/callback"
            else:
                # Fallback to localhost for development
                redirect_uri = "http://localhost:8000/api/oauth/google/callback"
        
        if not all([client_id, client_secret]):
            return False, "Google OAuth credentials missing"
        
        try:
            response = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            })
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if not access_token:
                return False, "No access token received from Google"
            
            # Calculate expires_at
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
            
            # Store tokens via AuthService
            await auth_service.store_google_token(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                extra_data=token_data
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"Google OAuth callback error: {e}", exc_info=True)
            return False, f"Auth failed: {str(e)}"
    
    @staticmethod
    def get_ticktick_auth_url(user_id: str) -> str:
        """
        Generate TickTick OAuth authorization URL.
        
        Args:
            user_id: User ID to associate with this OAuth flow
            
        Returns:
            Authorization URL string
        """
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        redirect_uri = os.getenv("TICKTICK_REDIRECT_URI")
        
        if not client_id:
            raise ValueError("TICKTICK_CLIENT_ID not configured")
        
        if not redirect_uri:
            # Try to construct from Cloud Run URL
            cloud_run_url = os.getenv("CLOUD_RUN_URL")
            if cloud_run_url:
                redirect_uri = f"{cloud_run_url}/api/oauth/ticktick/callback"
            else:
                raise ValueError("TICKTICK_REDIRECT_URI not configured and CLOUD_RUN_URL not available")
        
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Clean up expired states
        _cleanup_expired_oauth_states()
        
        # Store state -> user_id mapping (10 min TTL)
        _oauth_states[state] = (user_id, datetime.utcnow() + timedelta(minutes=10))
        
        params = {
            "scope": "tasks:write tasks:read",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state
        }
        
        return f"https://ticktick.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    async def handle_ticktick_callback(code: str, state: str) -> Tuple[bool, Optional[str]]:
        """
        Handle TickTick OAuth callback.
        
        Args:
            code: Authorization code from TickTick
            state: State parameter for CSRF protection
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Validate state
        if state not in _oauth_states:
            return False, "Invalid or expired state parameter"
        
        user_id, expires_at = _oauth_states[state]
        
        if datetime.utcnow() > expires_at:
            del _oauth_states[state]
            return False, "State parameter expired"
        
        # Clean up used state
        del _oauth_states[state]
        
        # Exchange code for tokens
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        redirect_uri = os.getenv("TICKTICK_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            return False, "TickTick OAuth credentials missing"
        
        try:
            response = requests.post("https://ticktick.com/oauth/token", data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "scope": "tasks:write tasks:read"
            })
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            
            if not access_token:
                return False, "No access token received from TickTick"
            
            # Calculate expires_at
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
            
            # Store tokens via AuthService
            await auth_service.store_ticktick_token(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                extra_data=token_data
            )
            
            return True, None
            
        except Exception as e:
            logger.error(f"TickTick OAuth callback error: {e}", exc_info=True)
            return False, f"Auth failed: {str(e)}"


# Singleton instance
oauth_service = OAuthService()

