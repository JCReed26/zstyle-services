"""
Google OAuth2 endpoints.

Handles OAuth2 flow for Google services (Calendar, Gmail, etc.).
"""
import secrets
import time
from typing import Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, HTTPException
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from services import credential_service
from core.config import settings

router = APIRouter()

# In-memory state storage
# In production, use Redis or similar distributed cache
_oauth_states: Dict[str, Dict[str, Any]] = {}

# State expiration time (10 minutes)
STATE_EXPIRATION_SECONDS = 600


def _build_authorization_url(state: str) -> str:
    """
    Build Google OAuth2 authorization URL.
    
    Args:
        state: OAuth state token for CSRF protection
        
    Returns:
        Authorization URL
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. GOOGLE_CLIENT_ID is required."
        )
    
    redirect_uri = f"http://localhost:{settings.PORT}/oauth/google/callback"
    scope = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.readonly"
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "code",
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Always show consent screen to get refresh token
        "state": state
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


@router.get("/oauth/google/initiate")
async def initiate_google_oauth(user_id: str = Query(..., description="User ID for OAuth flow")):
    """
    Initiate Google OAuth2 flow.
    
    Generates a secure state token and returns the authorization URL.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with authorization URL and state token
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required."
        )
    
    # Generate secure state token
    state = secrets.token_urlsafe(32)
    
    # Store state with user_id and timestamp
    _oauth_states[state] = {
        "user_id": user_id,
        "timestamp": time.time()
    }
    
    # Build authorization URL
    url = _build_authorization_url(state)
    
    return {"url": url, "state": state}


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token from initiation")
):
    """
    Handle Google OAuth2 callback.
    
    Validates state, exchanges authorization code for tokens, and stores credentials.
    
    Args:
        code: Authorization code from Google
        state: State token from initiation
        
    Returns:
        Dictionary with success status and user_id
    """
    # Validate state
    if state not in _oauth_states:
        raise HTTPException(
            status_code=400,
            detail="Invalid state token. The OAuth flow may have expired or been tampered with."
        )
    
    state_data = _oauth_states[state]
    user_id = state_data["user_id"]
    
    # Check if state has expired
    if time.time() - state_data["timestamp"] > STATE_EXPIRATION_SECONDS:
        del _oauth_states[state]
        raise HTTPException(
            status_code=400,
            detail="State token has expired. Please initiate a new OAuth flow."
        )
    
    # Remove state immediately (one-time use)
    del _oauth_states[state]
    
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured."
        )
    
    try:
        # Create OAuth2 flow
        redirect_uri = f"http://localhost:{settings.PORT}/oauth/google/callback"
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.readonly"],
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        
        # Get credentials
        credentials: Credentials = flow.credentials
        
        # Prepare credentials for storage
        credentials_dict: Dict[str, Any] = {
            "token": credentials.token,
            "token_type": "Bearer"
        }
        
        if credentials.refresh_token:
            credentials_dict["refresh_token"] = credentials.refresh_token
        
        if credentials.expiry:
            # Convert datetime to timestamp
            credentials_dict["expires_at"] = credentials.expiry.timestamp()
        
        if credentials.scopes:
            credentials_dict["scope"] = " ".join(credentials.scopes)
        
        # Store credentials
        await credential_service.store_credentials(
            user_id=user_id,
            service="google",
            credentials=credentials_dict
        )
        
        return {
            "status": "success",
            "user_id": user_id
        }
        
    except Exception as e:
        # Log error details server-side
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Google OAuth token exchange failed: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange authorization code for tokens: {str(e)}"
        )
