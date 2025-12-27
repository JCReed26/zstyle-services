"""
Tools for the Executive Function Coach Agent

These are the tools available to the exec_func_coach agent.
Each tool is a function that can be called by the agent to perform actions.

ADDING A NEW TOOL:
==================

1. Define the function with proper type hints and docstring:

    async def my_tool(
        param1: str,
        param2: int,
        tool_context: ToolContext  # ADK injects this
    ) -> Dict[str, Any]:
        '''
        Short description of what this tool does.
        
        Args:
            param1: Description of param1
            param2: Description of param2
            
        Returns:
            Dictionary with result data.
        '''
        # Implementation here
        return {"status": "success", "data": result}

2. Add the tool to the agent's tools list in agent.py:
    tools=[..., my_tool]

3. Update the agent's instruction to explain when to use the tool.

IMPORTANT: Always handle errors gracefully and return status dictionaries.
"""
import os
import requests
import json
import datetime
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.adk.tools import ToolContext
from google.adk.auth.credential_manager import CredentialManager
import urllib.parse


from database.core import AsyncSessionLocal
from database.models import Credential, MemorySlot, CredentialType
from services.memory import memory_service
from services.memory.openmemory_service import openmemory_service

# Import ContextVar from router for user_id fallback
try:
    from channels.router import _current_user_id
except ImportError:
    # Fallback if import fails
    import contextvars
    _current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_user_id", default=None)

# OAuth state storage for CSRF protection
# Format: {state: (user_id, expires_at)}
_oauth_states: Dict[str, Tuple[str, datetime.datetime]] = {}


def _cleanup_expired_oauth_states():
    """Remove expired OAuth states from storage."""
    global _oauth_states
    now = datetime.datetime.utcnow()
    expired = [state for state, (_, expires_at) in _oauth_states.items() if now > expires_at]
    for state in expired:
        del _oauth_states[state]


async def _get_credential(user_id: Optional[str], credential_type: str) -> Optional[Dict[str, Any]]:
    """
    Get a credential from the database.
    
    This is a helper function - credentials are stored securely
    in the Credential table.
    
    Args:
        user_id: User ID (can be None, will try to get from ContextVar or tool_context)
        credential_type: Type of credential to retrieve
    """
    from sqlalchemy import select, and_
    
    # If user_id not provided, try to get from ContextVar (fallback mechanism)
    if not user_id:
        user_id = _current_user_id.get()
    
    if not user_id:
        return None
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Credential).where(
                and_(
                    Credential.user_id == user_id,
                    Credential.credential_type == credential_type,
                    Credential.is_active == True
                )
            )
        )
        cred = result.scalar_one_or_none()
        
        if not cred:
            return None
        
        # Check if expired and try to refresh if refresh_token exists
        if cred.is_expired() and cred.refresh_token:
            # Attempt token refresh based on credential type
            refreshed = False
            if credential_type == CredentialType.TICKTICK_TOKEN:
                refreshed = await _refresh_ticktick_token(user_id, cred.refresh_token)
            elif credential_type == CredentialType.GOOGLE_OAUTH:
                refreshed = await _refresh_google_token(user_id, cred.refresh_token)
            
            if refreshed:
                # Re-fetch the credential after refresh
                result = await db.execute(
                    select(Credential).where(
                        and_(
                            Credential.user_id == user_id,
                            Credential.credential_type == credential_type,
                            Credential.is_active == True
                        )
                    )
                )
                cred = result.scalar_one_or_none()
        
        if cred and not cred.is_expired():
            return {
                "token": cred.token_value,
                "refresh_token": cred.refresh_token,
                "extra_data": cred.extra_data
            }
    return None


async def _refresh_ticktick_token(user_id: str, refresh_token: str) -> bool:
    """
    Refresh a TickTick access token using the refresh token.
    
    Returns True if refresh successful, False otherwise.
    """
    client_id = os.getenv("TICKTICK_CLIENT_ID")
    client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
    
    if not all([client_id, client_secret]):
        return False
    
    try:
        response = requests.post("https://ticktick.com/oauth/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        })
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data.get("access_token")
        if not access_token:
            return False
        
        # Calculate expires_at
        expires_at = None
        if "expires_in" in token_data:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
        
        # Update credential in database
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.TICKTICK_TOKEN
                )
            )
            cred = result.scalar_one_or_none()
            
            if cred:
                cred.token_value = access_token
                cred.expires_at = expires_at
                if "refresh_token" in token_data:
                    cred.refresh_token = token_data["refresh_token"]
                cred.extra_data = token_data
                await db.commit()
                return True
        
        return False
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to refresh TickTick token for user {user_id}: {e}")
        return False


# =============================================================================
# TICKTICK AUTH TOOLS
# =============================================================================

async def get_ticktick_auth_url(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the OAuth URL to authorize the TickTick integration.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        # Fallback to ContextVar
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User ID required for authentication."}
    
    client_id = os.getenv("TICKTICK_CLIENT_ID")
    redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", "http://localhost:8000/api/oauth/ticktick/callback")
    
    if not client_id:
        return {"status": "error", "message": "TICKTICK_CLIENT_ID not configured."}

    # Generate state parameter for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Store state -> user_id mapping (will be validated in callback)
    # Clean up expired states first
    _cleanup_expired_oauth_states()
    
    from datetime import datetime, timedelta
    if '_oauth_states' not in globals():
        globals()['_oauth_states'] = {}
    _oauth_states[state] = (user_id, datetime.utcnow() + timedelta(minutes=10))  # 10 min TTL
    
    params = {
        "scope": "tasks:write tasks:read",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state
    }
    
    auth_url = f"https://ticktick.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    return {
        "status": "success", 
        "message": "Click the link to authorize TickTick. You will be redirected back after authorization.",
        "auth_url": auth_url
    }

async def submit_ticktick_auth_code(
    code: str,
    tool_context: ToolContext = None,
    user_id: Optional[str] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Exchange the OAuth code for a token and securely store it.
    
    Can be called from tool context or directly with user_id (for callback endpoint).
    """
    # Get user_id from various sources
    if not user_id:
        if tool_context and tool_context.state:
            user_id = tool_context.state.get('user_id')
        if not user_id:
            user_id = _current_user_id.get()
    
    # Validate state if provided (from callback)
    if state:
        if state not in _oauth_states:
            return {"status": "error", "message": "Invalid or expired state parameter."}
        stored_user_id, expires_at = _oauth_states[state]
        from datetime import datetime
        if datetime.utcnow() > expires_at:
            del _oauth_states[state]
            return {"status": "error", "message": "State parameter expired. Please try again."}
        # Use user_id from state (more secure)
        user_id = stored_user_id
        # Clean up used state
        del _oauth_states[state]
    
    if not user_id:
        return {"status": "error", "message": "User ID required for authentication."}

    client_id = os.getenv("TICKTICK_CLIENT_ID")
    client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
    redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", "http://localhost:8000/api/oauth/ticktick/callback")

    if not all([client_id, client_secret]):
        return {"status": "error", "message": "TickTick credentials missing."}

    try:
        # Exchange code
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
        
        # Calculate expires_at from expires_in if provided
        expires_at = None
        if "expires_in" in token_data:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

        # Update Database
        async with AsyncSessionLocal() as db:
            # Check for existing credential
            from sqlalchemy import select
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.TICKTICK_TOKEN
                )
            )
            existing_cred = result.scalar_one_or_none()

            if existing_cred:
                existing_cred.token_value = access_token
                existing_cred.expires_at = expires_at
                existing_cred.extra_data = token_data
                # Refresh token might be present
                if "refresh_token" in token_data:
                    existing_cred.refresh_token = token_data["refresh_token"]
            else:
                new_cred = Credential(
                    user_id=user_id,
                    credential_type=CredentialType.TICKTICK_TOKEN,
                    token_value=access_token,
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=expires_at,
                    extra_data=token_data
                )
                db.add(new_cred)
            
            await db.commit()
        
        return {
            "status": "success", 
            "message": "TickTick authentication successful. Token stored."
        }

    except Exception as e:
        return {"status": "error", "message": f"Auth failed: {str(e)}"}

# =============================================================================
# GOOGLE OAUTH TOOLS
# =============================================================================

async def get_google_auth_url(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the OAuth URL to authorize Google (Gmail/Calendar) integration.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        # Fallback to ContextVar
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User ID required for authentication."}
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback")
    
    if not client_id:
        return {"status": "error", "message": "GOOGLE_CLIENT_ID not configured."}

    # Generate state parameter for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Clean up expired states first
    _cleanup_expired_oauth_states()
    
    from datetime import datetime, timedelta
    _oauth_states[state] = (user_id, datetime.utcnow() + timedelta(minutes=10))  # 10 min TTL
    
    # Google OAuth scopes for Gmail and Calendar
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
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen to get refresh token
        "state": state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    return {
        "status": "success", 
        "message": "Click the link to authorize Google (Gmail and Calendar). You will be redirected back after authorization.",
        "auth_url": auth_url
    }


async def submit_google_auth_code(
    code: str,
    tool_context: ToolContext = None,
    user_id: Optional[str] = None,
    state: Optional[str] = None
) -> Dict[str, Any]:
    """
    Exchange the OAuth code for Google tokens and securely store them.
    
    Can be called from tool context or directly with user_id (for callback endpoint).
    """
    # Get user_id from various sources
    if not user_id:
        if tool_context and tool_context.state:
            user_id = tool_context.state.get('user_id')
        if not user_id:
            user_id = _current_user_id.get()
    
    # Validate state if provided (from callback)
    if state:
        if state not in _oauth_states:
            return {"status": "error", "message": "Invalid or expired state parameter."}
        stored_user_id, expires_at = _oauth_states[state]
        from datetime import datetime
        if datetime.utcnow() > expires_at:
            del _oauth_states[state]
            return {"status": "error", "message": "State parameter expired. Please try again."}
        # Use user_id from state (more secure)
        user_id = stored_user_id
        # Clean up used state
        del _oauth_states[state]
    
    if not user_id:
        return {"status": "error", "message": "User ID required for authentication."}

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback")

    if not all([client_id, client_secret]):
        return {"status": "error", "message": "Google OAuth credentials missing."}

    try:
        # Exchange code for tokens using Google's token endpoint
        token_url = "https://oauth2.googleapis.com/token"
        response = requests.post(token_url, data={
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
            return {"status": "error", "message": "No access token received from Google."}
        
        # Calculate expires_at from expires_in if provided
        expires_at = None
        if "expires_in" in token_data:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

        # Store credential in database
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.GOOGLE_OAUTH
                )
            )
            existing_cred = result.scalar_one_or_none()

            if existing_cred:
                existing_cred.token_value = access_token
                existing_cred.expires_at = expires_at
                existing_cred.extra_data = token_data
                if refresh_token:
                    existing_cred.refresh_token = refresh_token
            else:
                new_cred = Credential(
                    user_id=user_id,
                    credential_type=CredentialType.GOOGLE_OAUTH,
                    token_value=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    extra_data=token_data
                )
                db.add(new_cred)
            
            await db.commit()
        
        return {
            "status": "success", 
            "message": "Google authentication successful. Gmail and Calendar access granted."
        }

    except Exception as e:
        logger.error(f"Google OAuth error: {e}", exc_info=True)
        return {"status": "error", "message": f"Auth failed: {str(e)}"}


async def _refresh_google_token(user_id: str, refresh_token: str) -> bool:
    """
    Refresh a Google access token using the refresh token.
    
    Returns True if refresh successful, False otherwise.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not all([client_id, client_secret]):
        return False
    
    try:
        token_url = "https://oauth2.googleapis.com/token"
        response = requests.post(token_url, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        })
        response.raise_for_status()
        token_data = response.json()
        
        access_token = token_data.get("access_token")
        if not access_token:
            return False
        
        # Calculate expires_at
        expires_at = None
        if "expires_in" in token_data:
            from datetime import datetime, timedelta, timezone
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
        
        # Update credential in database
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.GOOGLE_OAUTH
                )
            )
            cred = result.scalar_one_or_none()
            
            if cred:
                cred.token_value = access_token
                cred.expires_at = expires_at
                # Merge extra_data
                if cred.extra_data:
                    cred.extra_data.update(token_data)
                else:
                    cred.extra_data = token_data
                await db.commit()
                return True
        
        return False
    except Exception as e:
        logger.error(f"Failed to refresh Google token for user {user_id}: {e}")
        return False


# Update _get_credential to handle Google token refresh
# (This is already done above, but we need to add Google refresh logic)

async def get_current_goal(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the user's current goal from memory.
    
    Returns:
        The current goal data or a message if no goal is set.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    goal = await memory_service.get_memory_slot(user_id, MemorySlot.CURRENT_GOAL)
    
    if goal:
        return {"status": "success", "goal": goal}
    return {"status": "info", "message": "No current goal set. Would you like to set one?"}


async def set_current_goal(
    goal: str,
    deadline: Optional[str] = None,
    priority: int = 1,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Set the user's current goal.
    
    Args:
        goal: Description of the goal
        deadline: Optional deadline in YYYY-MM-DD format
        priority: Priority level (1-5, 1 being highest)
        
    Returns:
        Status of the operation.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    goal_data = {
        "goal": goal,
        "deadline": deadline,
        "priority": priority,
        "set_at": datetime.datetime.utcnow().isoformat()
    }
    
    await memory_service.set_memory_slot(
        user_id=user_id,
        slot=MemorySlot.CURRENT_GOAL,
        value=goal_data,
        description=f"Goal: {goal}"
    )
    
    return {"status": "success", "message": f"Goal set: {goal}", "data": goal_data}


async def get_user_preferences(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get user preferences from memory.
    
    Returns:
        User preferences or defaults.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    prefs = await memory_service.get_memory_slot(user_id, MemorySlot.USER_PREFERENCES)
    
    if prefs:
        return {"status": "success", "preferences": prefs}
    return {
        "status": "info", 
        "message": "No preferences set yet",
        "preferences": {"timezone": "UTC", "temp_unit": "C"}  # Defaults
    }

async def get_user_context(
    tool_context: ToolContext,
    include_flexible: bool = False,
    flexible_tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Retrieve the aggregated user context for the current user.

    Args:
        tool_context: ToolContext injected by ADK (with user_id in state)
        include_flexible: Whether to include flexible (tagged) memories
        flexible_tags: Filter flexible memories by these tags
        
    Returns:
        Dictionary containing user context or error.
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}

    try:
        context = await memory_service.get_user_context(
            user_id=user_id,
            include_flexible=include_flexible,
            flexible_tags=flexible_tags
        )
        return {"status": "success", "context": context}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def add_long_term_memory(
    content: str,
    tags: Optional[List[str]] = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Add a memory to the long-term vector storage for semantic retrieval.
    Use this for facts, observations, or thoughts that should be recallable later.
    
    Args:
        content: The text content to remember
        tags: Optional list of tags for categorization
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    if not openmemory_service:
        return {"status": "error", "message": "Long-term memory service not available"}

    try:
        result = await openmemory_service.add_memory(
            user_id=user_id,
            content=content,
            metadata={"tags": tags} if tags else {}
        )
        return {"status": "success", "message": "Memory stored in long-term storage", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to store memory: {str(e)}"}


async def search_long_term_memory(
    query: str,
    limit: int = 5,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Search long-term memory for relevant information using semantic search.
    
    Args:
        query: The search query
        limit: Max number of results (default 5)
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}

    if not openmemory_service:
        return {"status": "error", "message": "Long-term memory service not available"}

    try:
        results = await openmemory_service.search_memories(
            user_id=user_id,
            query=query,
            limit=limit
        )
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {str(e)}"}


# =============================================================================