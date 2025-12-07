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
import datetime
import asyncio
from typing import Dict, Any, List, Optional
import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.adk.tools import ToolContext

from database.engine import AsyncSessionLocal
from database.models import Credential, MemorySlot
from services.memory import memory_service


async def _get_credential(user_id: str, credential_type: str) -> Optional[Dict[str, Any]]:
    """
    Get a credential from the database.
    
    This is a helper function - credentials are stored securely
    in the Credential table, isolated from RAG.
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


async def _get_calendar_service(tool_context: ToolContext):
    """Get Google Calendar service for the current user."""
    user_id = tool_context.state.get('user_id')
    if not user_id:
        raise ValueError("User ID not found in session state. Please authenticate first.")
    
    token_data = await _get_credential(user_id, "google_calendar")
    if not token_data:
        raise ValueError("No Google Calendar credentials found. Please authenticate with Google first.")
    
    extra = token_data.get('extra_data', {})
    creds = Credentials(
        token=token_data['token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri=extra.get('token_uri'),
        client_id=extra.get('client_id'),
        client_secret=extra.get('client_secret'),
        scopes=extra.get('scopes')
    )
    
    return build('calendar', 'v3', credentials=creds)


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


# =============================================================================
# CALENDAR TOOLS
# =============================================================================

async def get_user_calendar_events(
    start_date: str, 
    end_date: str, 
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Get calendar events for the authenticated user within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (e.g. "2023-10-27")
        end_date: End date in YYYY-MM-DD format (e.g. "2023-10-28")
        
    Returns:
        Dictionary containing list of events.
    """
    try:
        service = await _get_calendar_service(tool_context)
        
        # Convert to RFC3339 format
        time_min = f"{start_date}T00:00:00Z"
        time_max = f"{end_date}T23:59:59Z"
        
        # Create the request object but don't execute it yet
        request = service.events().list(
            calendarId='primary', 
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        )
        # Run the blocking .execute() in a separate thread
        events_result = await asyncio.to_thread(request.execute)
        
        events = events_result.get('items', [])
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            formatted_events.append({
                "id": event['id'],
                "summary": event.get('summary', 'No Title'),
                "start": start,
                "status": event.get('status')
            })
            
        return {"events": formatted_events, "count": len(formatted_events)}
        
    except ValueError as e:
        # Auth not set up
        return {"status": "auth_required", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def add_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Add a new event to the user's primary calendar.
    
    Args:
        summary: Title of the event
        start_time: Start time in RFC3339 format (e.g., "2023-10-27T10:00:00Z")
        end_time: End time in RFC3339 format (e.g., "2023-10-27T11:00:00Z")
        description: Description of the event
        
    Returns:
        Dictionary with created event details.
    """
    try:
        service = await _get_calendar_service(tool_context)
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        request = service.events().insert(calendarId='primary', body=event)
        event = await asyncio.to_thread(request.execute)
        return {"status": "success", "event_id": event.get('id'), "link": event.get('htmlLink')}

    except ValueError as e:
        return {"status": "auth_required", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_calendar_event(
    event_id: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Delete a calendar event by ID.
    
    Args:
        event_id: The unique ID of the event to delete.
        
    Returns:
        Status dictionary.
    """
    try:
        service = await _get_calendar_service(tool_context)
        request = service.events().delete(calendarId='primary', eventId=event_id)
        await asyncio.to_thread(request.execute)
        return {"status": "success", "message": "Event deleted successfully."}
    except ValueError as e:
        return {"status": "auth_required", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_reminder(
    title: str, 
    date: str, 
    time: str, 
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Create a reminder (as a 30-min calendar event).
    
    Args:
        title: Title of the reminder
        date: Date in YYYY-MM-DD
        time: Time in HH:MM
        
    Returns:
        Status.
    """
    dt_obj = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end_obj = dt_obj + datetime.timedelta(minutes=30)
    
    start_str = dt_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    return await add_calendar_event(
        summary=f"Reminder: {title}",
        start_time=start_str,
        end_time=end_str,
        description="Created via Executive Coach Agent",
        tool_context=tool_context
    )


# =============================================================================
# TASK TOOLS (Placeholders)
# =============================================================================

async def get_task_list(list_name: str = "default", tool_context: ToolContext = None) -> Dict[str, Any]:
    """
    Get tasks from the task management system.
    
    Note: This is a placeholder. TickTick/Task integration not yet implemented.
    """
    return {"status": "info", "message": "Task integration not yet set up. Use calendar events or set goals instead."}


async def add_task(
    title: str, 
    description: str = "", 
    due_date: str = None,
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Add a task to the task management system.
    
    Note: This is a placeholder. TickTick/Task integration not yet implemented.
    """
    return {"status": "info", "message": "Task integration not yet set up. Use calendar events or set goals instead."}
