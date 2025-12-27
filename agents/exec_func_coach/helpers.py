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
from typing import Dict, Any, List, Optional
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


async def _get_credential(user_id: str, credential_type: str) -> Optional[Dict[str, Any]]:
    """
    Get a credential from the database.
    
    This is a helper function - credentials are stored securely
    in the Credential table.
    """
    from sqlalchemy import select, and_
    
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
        
        if cred and not cred.is_expired():
            return {
                "token": cred.token_value,
                "refresh_token": cred.refresh_token,
                "extra_data": cred.extra_data
            }
    return None


# =============================================================================
# TICKTICK AUTH TOOLS
# =============================================================================

async def get_ticktick_auth_url(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the OAuth URL to authorize the TickTick integration.
    """
    client_id = os.getenv("TICKTICK_CLIENT_ID")
    redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", "http://localhost:8000/callback")
    
    if not client_id:
        return {"status": "error", "message": "TICKTICK_CLIENT_ID not configured."}

    params = {
        "scope": "tasks:write tasks:read",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code"
    }
    
    auth_url = f"https://ticktick.com/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    return {
        "status": "success", 
        "message": "Click the link to authorize TickTick, then copy the code from the redirect URL.",
        "auth_url": auth_url
    }

async def submit_ticktick_auth_code(
    code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Exchange the OAuth code for a token and securely store it.
    """
    user_id = tool_context.state.get('user_id')
    if not user_id:
        return {"status": "error", "message": "User ID required for authentication."}

    client_id = os.getenv("TICKTICK_CLIENT_ID")
    client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
    redirect_uri = os.getenv("TICKTICK_REDIRECT_URI", "http://localhost:8000/callback")

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
                    extra_data=token_data
                )
                db.add(new_cred)
            
            await db.commit()

        # Update current process env for immediate use if possible
        os.environ["TICKTICK_ACCESS_TOKEN"] = access_token
        
        return {
            "status": "success", 
            "message": "TickTick authentication successful. Token stored."
        }

    except Exception as e:
        return {"status": "error", "message": f"Auth failed: {str(e)}"}

# =============================================================================
# MEMORY TOOLS
# =============================================================================

async def get_current_goal(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the user's current goal from memory.
    
    Returns:
        The current goal data or a message if no goal is set.
    """
    user_id = tool_context.state.get('user_id')
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
    user_id = tool_context.state.get('user_id')
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
    user_id = tool_context.state.get('user_id')
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
    user_id = tool_context.state.get('user_id')
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
    user_id = tool_context.state.get('user_id')
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
    user_id = tool_context.state.get('user_id')
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