"""
TickTick OAuth2 endpoints.

Handles OAuth2 flow for TickTick task management service.
"""
import secrets
import time
import asyncio
from typing import Dict, Any

from fastapi import APIRouter, Query, HTTPException
from ticktick.oauth2 import OAuth2

from services import credential_service
from core.config import settings

router = APIRouter()

# In-memory state storage
# In production, use Redis or similar distributed cache
_oauth_states: Dict[str, Dict[str, Any]] = {}

# State expiration time (10 minutes)
STATE_EXPIRATION_SECONDS = 600


@router.get("/oauth/ticktick/initiate")
async def initiate_ticktick_oauth(user_id: str = Query(..., description="User ID for OAuth flow")):
    """
    Initiate TickTick OAuth2 flow.
    
    Generates a secure state token and returns the authorization URL.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with authorization URL and state token
    """
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="TickTick OAuth not configured. TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET are required."
        )
    
    # Generate secure state token
    state = secrets.token_urlsafe(32)
    
    # Store state with user_id and timestamp
    _oauth_states[state] = {
        "user_id": user_id,
        "timestamp": time.time()
    }
    
    # Create OAuth2 client
    redirect_uri = f"http://localhost:{settings.PORT}/oauth/ticktick/callback"
    oauth_client = OAuth2(
        client_id=settings.TICKTICK_CLIENT_ID,
        client_secret=settings.TICKTICK_CLIENT_SECRET,
        redirect_uri=redirect_uri
    )
    
    # Get authorization URL
    # Note: ticktick-py's get_authorization_url may need state parameter
    # If it doesn't support state, we'll need to append it manually
    try:
        auth_url = await asyncio.to_thread(oauth_client.get_authorization_url, state=state)
    except TypeError:
        # If get_authorization_url doesn't accept state, get base URL and append state
        auth_url = await asyncio.to_thread(oauth_client.get_authorization_url)
        if "state=" not in auth_url:
            separator = "&" if "?" in auth_url else "?"
            auth_url = f"{auth_url}{separator}state={state}"
    
    return {"url": auth_url, "state": state}


@router.get("/oauth/ticktick/callback")
async def ticktick_oauth_callback(
    code: str = Query(..., description="Authorization code from TickTick"),
    state: str = Query(..., description="State token from initiation")
):
    """
    Handle TickTick OAuth2 callback.
    
    Validates state, exchanges authorization code for tokens, and stores credentials.
    
    Args:
        code: Authorization code from TickTick
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
    
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="TickTick OAuth not configured."
        )
    
    try:
        # Create OAuth2 client
        redirect_uri = f"http://localhost:{settings.PORT}/oauth/ticktick/callback"
        oauth_client = OAuth2(
            client_id=settings.TICKTICK_CLIENT_ID,
            client_secret=settings.TICKTICK_CLIENT_SECRET,
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for tokens
        token_response = await asyncio.to_thread(
            oauth_client.get_access_token,
            code
        )
        
        # Extract token information
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        
        # Calculate expiration timestamp
        expires_at = int(time.time()) + expires_in
        
        # Prepare credentials for storage
        credentials_dict: Dict[str, Any] = {
            "token": access_token,
            "expires_at": expires_at,
            "expires_in": expires_in
        }
        
        if refresh_token:
            credentials_dict["refresh_token"] = refresh_token
        
        # Store credentials
        await credential_service.store_credentials(
            user_id=user_id,
            service="ticktick",
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
        logger.error(f"TickTick OAuth token exchange failed: {e}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange authorization code for tokens: {str(e)}"
        )
