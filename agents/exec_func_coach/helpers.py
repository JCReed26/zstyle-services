"""
Tools for the Executive Function Coach Agent

These are the tools available to the exec_func_coach agent.
Each tool is a function that can be called by the agent to perform actions.

IMPORTANT: OAuth and credential management has been moved to services/auth/
Agents NEVER handle tokens or OAuth codes directly.
"""
from typing import Dict, Any, List, Optional
import datetime
import logging

from google.adk.tools import ToolContext

from services.memory import memory_service
from services.memory.openmemory_service import openmemory_service
from database.models import MemorySlot

# Import ContextVar from router for user_id fallback
try:
    from channels.router import _current_user_id
except ImportError:
    # Fallback if import fails
    import contextvars
    _current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_user_id", default=None)

# Logger for OAuth URL logging
logger = logging.getLogger(__name__)

# =============================================================================
# MEMORY TOOLS
# =============================================================================
# Note: OAuth and credential functions removed - moved to services/auth/
# Agents never handle tokens or OAuth codes directly

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
# OAUTH INITIATION TOOLS
# =============================================================================
# These tools allow the agent to initiate OAuth flows.
# The OAuth URL is logged - the agent never sees tokens or codes.
# The OAuth callback handles token storage automatically.

async def initiate_ticktick_auth(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Initiate TickTick OAuth authorization flow.
    
    The authorization URL is logged to the application logs.
    Check the logs to find the URL and complete authorization.
    After authorization, tokens are automatically stored - the agent never sees them.
    
    Returns:
        Dictionary with status and instructions to check logs
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    try:
        from services.auth.oauth_service import oauth_service
        auth_url = oauth_service.get_ticktick_auth_url(user_id)
        
        # Log the URL prominently
        logger.info("=" * 80)
        logger.info("TICKTICK OAUTH AUTHORIZATION REQUIRED")
        logger.info("=" * 80)
        logger.info(f"User ID: {user_id}")
        logger.info(f"Authorization URL: {auth_url}")
        logger.info("=" * 80)
        logger.info("Please visit the URL above to authorize TickTick access.")
        logger.info("After authorization, TickTick features will be available.")
        logger.info("=" * 80)
        
        return {
            "status": "success",
            "message": "TickTick authorization URL has been generated and logged. Please check the application logs for the authorization URL. After you authorize TickTick, you can use TickTick features."
        }
    except Exception as e:
        logger.error(f"Failed to generate TickTick authorization URL: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate TickTick authorization URL: {str(e)}"
        }


async def initiate_google_auth(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Initiate Google OAuth authorization flow (for Gmail and Calendar).
    
    The authorization URL is logged to the application logs.
    Check the logs to find the URL and complete authorization.
    After authorization, tokens are automatically stored - the agent never sees them.
    
    Returns:
        Dictionary with status and instructions to check logs
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    try:
        from services.auth.oauth_service import oauth_service
        auth_url = oauth_service.get_google_auth_url(user_id)
        
        # Log the URL prominently
        logger.info("=" * 80)
        logger.info("GOOGLE OAUTH AUTHORIZATION REQUIRED")
        logger.info("=" * 80)
        logger.info(f"User ID: {user_id}")
        logger.info(f"Authorization URL: {auth_url}")
        logger.info("=" * 80)
        logger.info("Please visit the URL above to authorize Google (Gmail/Calendar) access.")
        logger.info("After authorization, Gmail and Calendar features will be available.")
        logger.info("=" * 80)
        
        return {
            "status": "success",
            "message": "Google authorization URL has been generated and logged. Please check the application logs for the authorization URL. After you authorize Google, you can use Gmail and Calendar features."
        }
    except Exception as e:
        logger.error(f"Failed to generate Google authorization URL: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to generate Google authorization URL: {str(e)}"
        }


async def check_ticktick_auth_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Check if TickTick is authorized for the current user.
    
    Returns:
        Dictionary indicating whether TickTick is authorized
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    try:
        from services.auth import AuthService
        token = await AuthService.get_ticktick_token(user_id)
        
        if token:
            return {
                "status": "success",
                "authorized": True,
                "message": "TickTick is authorized and ready to use."
            }
        else:
            return {
                "status": "info",
                "authorized": False,
                "message": "TickTick is not authorized. Use initiate_ticktick_auth to generate an authorization URL (check logs for the URL)."
            }
    except Exception as e:
        logger.error(f"Failed to check TickTick authorization status: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to check TickTick authorization status: {str(e)}"
        }


async def check_google_auth_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Check if Google (Gmail/Calendar) is authorized for the current user.
    
    Returns:
        Dictionary indicating whether Google is authorized
    """
    user_id = tool_context.state.get('user_id') if tool_context.state else None
    if not user_id:
        user_id = _current_user_id.get()
    if not user_id:
        return {"status": "error", "message": "User not identified"}
    
    try:
        from services.auth import AuthService
        token = await AuthService.get_google_token(user_id)
        
        if token:
            return {
                "status": "success",
                "authorized": True,
                "message": "Google (Gmail and Calendar) is authorized and ready to use."
            }
        else:
            return {
                "status": "info",
                "authorized": False,
                "message": "Google is not authorized. Use initiate_google_auth to generate an authorization URL (check logs for the URL)."
            }
    except Exception as e:
        logger.error(f"Failed to check Google authorization status: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to check Google authorization status: {str(e)}"
        }
