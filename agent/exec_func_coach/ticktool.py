# ticktool.py
"""
TickTick Tool for the exec func coach 

implements the ticktick api using ticktick-py framework

TOOLCONTEXT INTEGRATION:
========================
All TickTick tool functions (add_task, get_tasks, update_task, delete_task, get_projects)
now accept an optional `tool_context` parameter that is automatically injected by ADK.

The tools use `_get_user_id_from_context()` to retrieve user_id from:
1. tool_context.state.get("user_id") - session state (preferred)
2. tool_context.session.user_id - session user_id property
3. tool_context.session.metadata.get("user_id") - session metadata
4. contextvars fallback - for backward compatibility during migration

This ensures user_id is properly accessible even when tools are called through nested
AgentTool wrappers, where contextvars may not propagate correctly.

The router stores user_id in session state before agent execution, ensuring it's
available to all tools via ToolContext.
"""

import logging
import contextvars
import asyncio
import httpx
from functools import wraps
from typing import Optional, Dict, Any, Callable

# Try to import ToolContext - may not be available in all ADK versions
try:
    from google.adk.tools import ToolContext
except ImportError:
    # Fallback if ToolContext not available
    ToolContext = None

from ticktick.oauth2 import OAuth2
from ticktick.api import TickTickClient
from services.credential_service import credential_service
from app.config import settings

logger = logging.getLogger(__name__)

# Context variable to store current user_id during tool execution
# This is set by the router before calling the agent
_current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_id', default=None)


# imports
# (ticktick-py imports are above)


# Retry decorator for authentication-sensitive operations
def retry_on_auth_error(max_retries: int = 3, initial_delay: float = 1.0):
    """Retry decorator for authentication-sensitive operations."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            result = None
            for attempt in range(max_retries):
                try:
                    result = await func(*args, **kwargs)
                    # Check if result indicates auth error
                    if isinstance(result, dict) and result.get("requires_auth"):
                        if attempt < max_retries - 1:
                            delay = initial_delay * (2 ** attempt)
                            logger.debug(f"Auth error on attempt {attempt + 1}, retrying in {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                    return result
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)
                        logger.debug(f"Error on attempt {attempt + 1}: {e}, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
            # After all retries failed
            if isinstance(result, dict) and result.get("requires_auth"):
                return result
            return {
                "success": False,
                "error": f"Operation failed after {max_retries} attempts: {str(last_error)}",
                "requires_auth": False
            }
        return wrapper
    return decorator


# helpers
async def refresh_ticktick_token(user_id: str, creds: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Refresh TickTick access token using refresh_token."""
    try:
        base_url = settings.OAUTH_BASE_URL or 'http://localhost:8000'
        redirect_uri = f"{base_url}/oauth/ticktick/callback"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://ticktick.com/oauth/token",
                data={
                    "client_id": settings.TICKTICK_CLIENT_ID,
                    "client_secret": settings.TICKTICK_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": creds.get("refresh_token"),
                    "redirect_uri": redirect_uri,
                }
            )
            response.raise_for_status()
            tokens = response.json()
            
            # Update credentials
            updated_creds = {
                "token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token") or creds.get("refresh_token"),  # Use new if provided
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in", 3600),
            }
            
            # Store updated credentials
            await credential_service.store_credentials(user_id, "ticktick", updated_creds)
            logger.info(f"Successfully refreshed TickTick token for user {user_id}")
            return updated_creds
    except Exception as e:
        logger.error(f"Token refresh failed for user {user_id}: {e}", exc_info=True)
        return None


async def get_ticktick_client(user_id: str) -> Optional[TickTickClient]:
    """Get TickTick client for user."""
    logger.debug(f"Getting TickTick client for user_id: {user_id}")
    
    # Validate user_id is not a placeholder
    if not user_id or user_id == "your user ID" or user_id.startswith("your"):
        logger.warning(f"Invalid user_id provided: {user_id}")
        return None
        
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        logger.warning("TickTick OAuth not configured")
        return None
    
    try:
        creds = await credential_service.get_credentials(user_id, "ticktick")
        logger.debug(f"Retrieved credentials: {bool(creds)}, keys: {list(creds.keys()) if creds else None}")
        
        if not creds:
            logger.debug(f"No TickTick credentials found for user {user_id}")
            return None
        
        redirect_uri = f"{settings.OAUTH_BASE_URL or 'http://localhost:8000'}/oauth/ticktick/callback"
        logger.debug(f"Using redirect_uri: {redirect_uri}")
        
        # Validate we have at least a token or refresh_token
        if not creds.get("token") and not creds.get("refresh_token"):
            logger.debug(f"No token or refresh_token found for user {user_id}")
            return None
        
        # Try to refresh token first if we only have refresh_token or token might be expired
        if creds.get("refresh_token") and (not creds.get("token") or len(str(creds.get("token", ""))) < 10):
            logger.debug(f"Token missing or appears invalid, attempting refresh for user {user_id}")
            updated_creds = await refresh_ticktick_token(user_id, creds)
            if updated_creds:
                creds = updated_creds
                logger.debug(f"Token refreshed successfully for user {user_id}")
            else:
                logger.warning(f"Token refresh failed for user {user_id}, credentials may need re-authentication")
                return None
        
        # If still no valid token after refresh attempt, return None
        if not creds.get("token"):
            logger.debug(f"No valid token available for user {user_id} after refresh attempt")
            return None
        
        # Create OAuth2 object with existing tokens to prevent interactive auth flow
        # CRITICAL: Pass check_cache=False to prevent OAuth2.__init__ from calling get_access_token()
        # which would trigger interactive OAuth flow (reading from stdin)
        auth = OAuth2(
            client_id=settings.TICKTICK_CLIENT_ID,
            client_secret=settings.TICKTICK_CLIENT_SECRET,
            redirect_uri=redirect_uri,
            check_cache=False  # Prevent automatic token retrieval that triggers interactive OAuth
        )
        # Set tokens explicitly AFTER creating object to avoid interactive flow
        auth.token = creds.get("token")
        auth.refresh_token = creds.get("refresh_token")
        
        logger.debug(f"Created OAuth2 object, token present: {bool(auth.token)}, refresh_token present: {bool(auth.refresh_token)}")
        logger.debug(f"Token length: {len(str(creds.get('token', '')))}, Refresh token present: {bool(creds.get('refresh_token'))}")
        
        # Create client - wrap sync() call to catch EOFError from interactive OAuth attempts
        client = TickTickClient(None, auth)
        
        # Try sync with retry and token refresh
        max_sync_retries = 3
        refreshed = False
        
        for attempt in range(max_sync_retries):
            try:
                logger.debug(f"Calling client.sync() for user {user_id} (attempt {attempt + 1}/{max_sync_retries})")
                client.sync()
                logger.info(f"Successfully synced TickTick client for user {user_id}")
                return client
            except EOFError as eof_error:
                # ticktick-py tried to do interactive OAuth (reading from stdin)
                # This happens when tokens are invalid and library tries browser flow
                logger.warning(f"TickTick attempted interactive OAuth (not supported in server environment): {eof_error}")
                # Try token refresh if we haven't already
                if attempt == 0 and auth.refresh_token and not refreshed:
                    try:
                        logger.debug(f"Attempting token refresh after EOFError for user {user_id}")
                        updated_creds = await refresh_ticktick_token(user_id, creds)
                        if updated_creds:
                            auth.token = updated_creds.get("token")
                            auth.refresh_token = updated_creds.get("refresh_token")
                            client = TickTickClient(None, auth)
                            refreshed = True
                            logger.debug(f"Token refreshed after EOFError, retrying sync for user {user_id}")
                            continue
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed after EOFError: {refresh_error}", exc_info=True)
                
                # If refresh didn't work or we've already tried, return None
                # User needs to re-authenticate via OAuth callback
                logger.warning(f"TickTick credentials invalid for user {user_id}, re-authentication required")
                return None
            except Exception as sync_error:
                logger.warning(f"TickTick sync failed (attempt {attempt + 1}): {sync_error}")
                
                # If we have refresh_token and haven't tried refreshing yet, attempt token refresh
                if attempt == 0 and auth.refresh_token and not refreshed:
                    try:
                        logger.debug(f"Attempting token refresh for user {user_id}")
                        updated_creds = await refresh_ticktick_token(user_id, creds)
                        if updated_creds:
                            # Update auth object with new token
                            auth.token = updated_creds.get("token")
                            auth.refresh_token = updated_creds.get("refresh_token")
                            # Recreate client with refreshed credentials
                            client = TickTickClient(None, auth)
                            refreshed = True
                            logger.debug(f"Token refreshed, retrying sync for user {user_id}")
                            continue
                        else:
                            logger.warning(f"Token refresh failed, will retry sync without refresh")
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed: {refresh_error}", exc_info=True)
                
                # If not last attempt, wait before retrying
                if attempt < max_sync_retries - 1:
                    delay = 1.0 * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    logger.debug(f"Retrying sync in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"TickTick sync failed after {max_sync_retries} attempts for {user_id}: {sync_error}", exc_info=True)
                    return None
        
        return None
    except Exception as e:
        logger.error(f"Failed to get TickTick credentials for user {user_id}: {e}", exc_info=True)
        return None


# oauth helpers
# (OAuth setup is handled in get_ticktick_client above)


# ticktick tool interface
# implement all of https://lazeroffmichael.github.io/ticktick-py/
class TickTickTool:
    """TickTick integration tool using ticktick-py framework."""
    

    async def add_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: int = 3,
    ) -> Dict[str, Any]:
        """Add task to TickTick.
        
        Args:
            user_id: User ID (automatically provided from context)
            title: Task title
            description: Optional task description
            project_id: Optional project ID
            priority: Priority level (1=Low, 3=Medium, 5=High)
        """
        # Validate user_id
        if not user_id or user_id == "your user ID" or user_id.startswith("your"):
            return {
                "success": False,
                "error": "Authentication required. Please authenticate your TickTick account.",
                "requires_auth": True
            }
        
        client = await get_ticktick_client(user_id)
        if not client:
            return {
                "success": False,
                "error": "TickTick not authenticated. Please authenticate your TickTick account to create tasks.",
                "requires_auth": True
            }
        
        try:
            task_data = client.task.builder(title=title, content=description or "", priority=priority)
            task_data["projectId"] = project_id or client.inbox_id
            created = client.task.create(task_data)
            return {"success": True, "task": {"id": created.get("id"), "title": created.get("title")}}
        except Exception as e:
            logger.error(f"Error creating task for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to create task: {str(e)}"}
    

    async def get_tasks(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get tasks from TickTick.
        
        Args:
            user_id: User ID (automatically provided from context)
            project_id: Optional project filter
            status: Optional status filter ("completed" or "uncompleted")
            search: Optional search query
        """
        # Validate user_id
        if not user_id or user_id == "your user ID" or user_id.startswith("your"):
            return {
                "success": False,
                "error": "Authentication required. Please authenticate your TickTick account.",
                "tasks": [],
                "requires_auth": True
            }
        
        client = await get_ticktick_client(user_id)
        if not client:
            return {
                "success": False,
                "error": "TickTick not authenticated. Please authenticate your TickTick account to access your tasks.",
                "tasks": [],
                "requires_auth": True
            }
        
        try:
            tasks = client.state.get("tasks", [])
            
            # Apply filters
            if project_id:
                tasks = [t for t in tasks if t.get("projectId") == project_id]
            if status == "completed":
                tasks = [t for t in tasks if t.get("status") == 2]
            elif status == "uncompleted":
                tasks = [t for t in tasks if t.get("status") != 2]
            if search:
                search_lower = search.lower()
                tasks = [t for t in tasks if search_lower in t.get("title", "").lower()]
            
            formatted = [
                {
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "status": "completed" if t.get("status") == 2 else "uncompleted",
                    "project_id": t.get("projectId")
                }
                for t in tasks
            ]
            return {
                "success": True,
                "tasks": formatted,
                "count": len(formatted)
            }
        except Exception as e:
            logger.error(f"Error getting tasks for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to retrieve tasks: {str(e)}",
                "tasks": []
            }
    

    async def update_task(
        self,
        user_id: str,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a TickTick task.
        
        Args:
            user_id: User ID (automatically provided from context)
            task_id: Task ID to update
            title: Optional new title
            description: Optional new description
            status: Optional status ("completed" or "uncompleted")
            priority: Optional priority level
        """
        # Validate user_id
        if not user_id or user_id == "your user ID" or user_id.startswith("your"):
            return {
                "success": False,
                "error": "Authentication required. Please authenticate your TickTick account.",
                "requires_auth": True
            }
        
        client = await get_ticktick_client(user_id)
        if not client:
            return {
                "success": False,
                "error": "TickTick not authenticated. Please authenticate your TickTick account to update tasks.",
                "requires_auth": True
            }
        
        try:
            task = client.get_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            if title:
                task["title"] = title
            if description:
                task["content"] = description
            if status == "completed":
                task["status"] = 2
            elif status == "uncompleted":
                task["status"] = 0
            if priority:
                task["priority"] = priority
            
            updated = client.task.update(task)
            return {"success": True, "task": {"id": updated.get("id"), "title": updated.get("title")}}
        except Exception as e:
            logger.error(f"Error updating task for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to update task: {str(e)}"}
    

    async def delete_task(
        self,
        user_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """Delete a TickTick task.
        
        Args:
            user_id: User ID (automatically provided from context)
            task_id: Task ID to delete
        """
        # Validate user_id
        if not user_id or user_id == "your user ID" or user_id.startswith("your"):
            return {
                "success": False,
                "error": "Authentication required. Please authenticate your TickTick account.",
                "requires_auth": True
            }
        
        client = await get_ticktick_client(user_id)
        if not client:
            return {
                "success": False,
                "error": "TickTick not authenticated. Please authenticate your TickTick account to delete tasks.",
                "requires_auth": True
            }
        
        try:
            task = client.get_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            client.task.delete(task)
            return {"success": True, "message": "Task deleted"}
        except Exception as e:
            logger.error(f"Error deleting task for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to delete task: {str(e)}"}
    

    async def get_projects(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get TickTick projects.
        
        Args:
            user_id: User ID (automatically provided from context)
        """
        # Validate user_id
        if not user_id or user_id == "your user ID" or user_id.startswith("your"):
            return {
                "success": False,
                "error": "Authentication required. Please authenticate your TickTick account.",
                "projects": [],
                "requires_auth": True
            }
        
        client = await get_ticktick_client(user_id)
        if not client:
            return {
                "success": False,
                "error": "TickTick not authenticated. Please authenticate your TickTick account to access your projects.",
                "projects": [],
                "requires_auth": True
            }
        
        try:
            projects = client.state.get("projects", [])
            formatted = [{"id": p.get("id"), "name": p.get("name")} for p in projects]
            return {"success": True, "projects": formatted, "count": len(formatted)}
        except Exception as e:
            logger.error(f"Error getting projects for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to retrieve projects: {str(e)}", "projects": []}


# Initialize tool instance
ticktick_tool = TickTickTool()


# Helper function to get user_id from ToolContext or contextvars
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


# Helper function to get user_id from context variable (backward compatibility)
def _get_user_id() -> Optional[str]:
    """Get user_id from context variable (backward compatibility fallback)."""
    try:
        user_id = _current_user_id.get()
        # Validate it's not a placeholder
        if user_id and user_id != "user_id" and not user_id.startswith("your"):
            logger.debug("Retrieved user_id from contextvars (fallback)")
            return user_id
        return None
    except LookupError:
        return None


# Wrapper functions that inject user_id from context
# These are the functions registered as tools - they don't require user_id parameter
@retry_on_auth_error(max_retries=3)
async def add_task(
    title: str,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    priority: int = 3,
    tool_context: Optional[Any] = None,  # ToolContext injected by ADK
) -> Dict[str, Any]:
    """Add task to TickTick. user_id is automatically provided from ToolContext or contextvars."""
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {
            "success": False,
            "error": "Authentication required. Please authenticate your TickTick account.",
            "requires_auth": True
        }
    return await ticktick_tool.add_task(user_id, title, description, project_id, priority)


@retry_on_auth_error(max_retries=3)
async def get_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    tool_context: Optional[Any] = None,  # ToolContext injected by ADK
) -> Dict[str, Any]:
    """Get tasks from TickTick. user_id is automatically provided from ToolContext or contextvars."""
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {
            "success": False,
            "error": "Authentication required. Please authenticate your TickTick account.",
            "tasks": [],
            "requires_auth": True
        }
    return await ticktick_tool.get_tasks(user_id, project_id, status, search)


@retry_on_auth_error(max_retries=3)
async def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    tool_context: Optional[Any] = None,  # ToolContext injected by ADK
) -> Dict[str, Any]:
    """Update a TickTick task. user_id is automatically provided from ToolContext or contextvars."""
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {
            "success": False,
            "error": "Authentication required. Please authenticate your TickTick account.",
            "requires_auth": True
        }
    return await ticktick_tool.update_task(user_id, task_id, title, description, status, priority)


@retry_on_auth_error(max_retries=3)
async def delete_task(
    task_id: str,
    tool_context: Optional[Any] = None,  # ToolContext injected by ADK
) -> Dict[str, Any]:
    """Delete a TickTick task. user_id is automatically provided from ToolContext or contextvars."""
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {
            "success": False,
            "error": "Authentication required. Please authenticate your TickTick account.",
            "requires_auth": True
        }
    return await ticktick_tool.delete_task(user_id, task_id)


@retry_on_auth_error(max_retries=3)
async def get_projects(
    tool_context: Optional[Any] = None,  # ToolContext injected by ADK
) -> Dict[str, Any]:
    """Get TickTick projects. user_id is automatically provided from ToolContext or contextvars."""
    user_id = _get_user_id_from_context(tool_context)
    if not user_id:
        return {
            "success": False,
            "error": "Authentication required. Please authenticate your TickTick account.",
            "projects": [],
            "requires_auth": True
        }
    return await ticktick_tool.get_projects(user_id)


# prompt for using ticktick tool and store in variable TICKTICK_PROMPT
TICKTICK_PROMPT = """
TickTick Task Management Tool

Use TickTick tools to help users manage their tasks and projects.

AVAILABLE OPERATIONS:
- add_task: Create a new task with title, optional description, project, and priority (1=Low, 3=Medium, 5=High)
- get_tasks: Retrieve tasks with optional filters (project_id, status, search query)
- update_task: Modify existing tasks (title, description, status, priority)
- delete_task: Remove tasks
- get_projects: List all available projects

IMPORTANT - USER_ID HANDLING:
- user_id is AUTOMATICALLY provided - you do NOT need to pass it as a parameter
- NEVER include user_id in your tool calls - it's handled automatically
- Tools will automatically use the correct user_id from the conversation context

AUTHENTICATION HANDLING:
- Tools automatically check authentication status
- If a tool returns {"success": False, "requires_auth": True}, inform the user they need to authenticate
- ONLY mention authentication when tools explicitly return authentication errors
- If tools succeed, proceed normally without mentioning authentication
- When authentication is needed, guide users to authenticate their TickTick account

BEST PRACTICES:
- Use get_projects first to help users find project IDs
- Default priority is 3 (Medium) if not specified
- Status values: "completed" or "uncompleted"
- Tasks are synced automatically - no need to manually refresh
- Call tools directly without user_id parameter - it's automatically provided
"""