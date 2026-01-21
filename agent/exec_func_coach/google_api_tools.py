"""
Google API Tools - Custom Implementation

Custom Google API tools that retrieve credentials per-request from the database,
following the proven TickTick pattern.

TOOLCONTEXT INTEGRATION:
========================
All Google API tool functions accept an optional `tool_context` parameter that is
automatically injected by ADK. The tools use `_get_user_id_from_context()` to
retrieve user_id from ToolContext, similar to TickTick tools.

This approach is more reliable than trying to inject credentials into ADK's
built-in Google toolsets, which don't easily support per-user credential injection.

ARCHITECTURE:
=============
1. Tools retrieve user_id from ToolContext
2. GoogleCredentialProvider retrieves credentials from database
3. Credentials are automatically refreshed if expired
4. Google API calls made with user-specific credentials
5. Errors handled with automatic retry and refresh
"""
import logging
import contextvars
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps

# Try to import ToolContext - may not be available in all ADK versions
try:
    from google.adk.tools import ToolContext
except ImportError:
    ToolContext = None

from services.google_credential_provider import get_google_credential_provider
from services.credential_service import credential_service
from app.config import settings

logger = logging.getLogger(__name__)

# Context variable for backward compatibility
_current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_id', default=None)


def _get_user_id() -> Optional[str]:
    """Get user_id from context variable (backward compatibility fallback)."""
    return _current_user_id.get()


def _get_user_id_from_context(tool_context: Optional[Any] = None) -> Optional[str]:
    """
    Get user_id from ToolContext, with fallback to contextvars.
    
    Tries multiple methods to get user_id:
    1. tool_context.state.get("user_id") - session state
    2. tool_context.session.user_id - session user_id property
    3. tool_context.session.metadata.get("user_id") - session metadata
    4. contextvars fallback for backward compatibility
    
    Args:
        tool_context: Optional ToolContext from ADK
        
    Returns:
        user_id string or None if not found
    """
    # Try ToolContext first if available
    if tool_context is not None:
        try:
            # Method 1: Check session state
            if hasattr(tool_context, 'state') and tool_context.state:
                user_id = tool_context.state.get("user_id")
                if user_id and user_id != "user_id" and not str(user_id).startswith("your"):
                    logger.debug("Retrieved user_id from tool_context.state")
                    return str(user_id)
            
            # Method 2: Check session.user_id property
            if hasattr(tool_context, 'session') and tool_context.session:
                if hasattr(tool_context.session, 'user_id'):
                    user_id = tool_context.session.user_id
                    if user_id and user_id != "user_id" and not str(user_id).startswith("your"):
                        logger.debug("Retrieved user_id from tool_context.session.user_id")
                        return str(user_id)
                
                # Method 3: Check session metadata
                if hasattr(tool_context.session, 'metadata') and tool_context.session.metadata:
                    user_id = tool_context.session.metadata.get("user_id")
                    if user_id and user_id != "user_id" and not str(user_id).startswith("your"):
                        logger.debug("Retrieved user_id from tool_context.session.metadata")
                        return str(user_id)
        except Exception as e:
            logger.debug(f"Error accessing user_id from ToolContext: {e}")
    
    # Fallback to contextvars (backward compatibility)
    return _get_user_id()


async def _get_google_api_client(
    user_id: str,
    tool_context: Optional[Any] = None
) -> Optional[httpx.AsyncClient]:
    """
    Get authenticated httpx client for Google API calls.
    
    Args:
        user_id: User ID
        tool_context: Optional ToolContext for credential caching
        
    Returns:
        Authenticated httpx.AsyncClient or None if credentials unavailable
    """
    credential_provider = get_google_credential_provider()
    creds = await credential_provider.get_credentials_for_user(
        user_id,
        tool_context,
        service="google"
    )
    
    if not creds:
        logger.debug(f"No Google credentials available for user {user_id}")
        return None
    
    access_token = creds.get("access_token")
    if not access_token:
        logger.warning(f"No access_token in credentials for user {user_id}")
        return None
    
    # Create authenticated client
    client = httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        timeout=30.0
    )
    
    return client


async def _call_google_api_with_retry(
    user_id: str,
    tool_context: Optional[Any],
    api_call: callable,
    max_retries: int = 2
) -> Any:
    """
    Call Google API with automatic token refresh on 401/403 errors.
    
    Args:
        user_id: User ID
        tool_context: Optional ToolContext
        api_call: Async function that makes the API call
        max_retries: Maximum retry attempts
        
    Returns:
        API response or raises exception
    """
    credential_provider = get_google_credential_provider()
    
    for attempt in range(max_retries + 1):
        try:
            return await api_call()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403) and attempt < max_retries:
                logger.warning(f"Google API returned {e.response.status_code}, attempting token refresh...")
                
                # Clear cached credentials
                cred_key = f"auth:google:{user_id}"
                if tool_context and hasattr(tool_context, 'state') and tool_context.state:
                    tool_context.state.pop(cred_key, None)
                
                # Try to refresh token
                creds = await credential_service.get_credentials(user_id, "google")
                if creds and creds.get("refresh_token"):
                    refreshed = await credential_provider._refresh_token(user_id, creds, "google")
                    if refreshed:
                        logger.info(f"Token refreshed successfully, retrying API call...")
                        continue
                
                # If refresh failed, credentials may be revoked
                logger.error(f"Token refresh failed or credentials revoked for user {user_id}")
                raise CredentialError("Google credentials invalid, re-authentication required")
            
            # Re-raise if not a retryable error or max retries reached
            raise
    
    raise Exception("Max retries exceeded")


# Google Calendar Tools

async def get_calendar_events(
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Get Google Calendar events for the user.
    
    Args:
        max_results: Maximum number of events to return (default: 10)
        time_min: Lower bound (exclusive) for an event's start time (ISO 8601)
        time_max: Upper bound (exclusive) for an event's end time (ISO 8601)
        tool_context: Optional ToolContext injected by ADK
        
    Returns:
        Dictionary with events list and metadata
    """
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {"success": False, "error": "User ID not found in context"}
    
    async def _make_request():
        client = await _get_google_api_client(user_id, tool_context)
        if not client:
            raise CredentialError("Google credentials not available")
        
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    try:
        data = await _call_google_api_with_retry(user_id, tool_context, _make_request)
        events = data.get("items", [])
        return {
            "success": True,
            "events": events,
            "count": len(events)
        }
    except CredentialError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to retrieve calendar events: {str(e)}"}


async def create_calendar_event(
    summary: str,
    description: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    location: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Create a Google Calendar event.
    
    Args:
        summary: Event title
        description: Event description
        start_time: Start time (ISO 8601)
        end_time: End time (ISO 8601)
        location: Event location
        tool_context: Optional ToolContext injected by ADK
        
    Returns:
        Dictionary with created event or error
    """
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {"success": False, "error": "User ID not found in context"}
    
    async def _make_request():
        client = await _get_google_api_client(user_id, tool_context)
        if not client:
            raise CredentialError("Google credentials not available")
        
        event_data = {
            "summary": summary
        }
        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        
        if start_time or end_time:
            event_data["start"] = {"dateTime": start_time or datetime.now().isoformat()}
            event_data["end"] = {"dateTime": end_time or start_time or datetime.now().isoformat()}
        
        response = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            json=event_data
        )
        response.raise_for_status()
        return response.json()
    
    try:
        event = await _call_google_api_with_retry(user_id, tool_context, _make_request)
        return {
            "success": True,
            "event": event,
            "event_id": event.get("id")
        }
    except CredentialError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to create calendar event: {str(e)}"}


# Placeholder for Gmail and Tasks tools
# These can be implemented similarly following the same pattern

class CredentialError(Exception):
    """Raised when credentials are invalid or unavailable."""
    pass
