"""Tools for the Executive Function Coach agent."""

import datetime
from typing import Dict, Any, List, Optional
import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.adk.tools import ToolContext

from database.sqlite_db import get_db_session
from services.auth.credential_service import credential_service

# Helper to get the service
async def _get_calendar_service(tool_context: ToolContext):
    user_db_id_str = tool_context.state.get('user_db_id')
    if not user_db_id_str:
        raise ValueError("User ID not found in session state. Please authenticate first.")
    
    user_id = uuid.UUID(user_db_id_str)
    
    # We need a DB session. Since we are in an async tool, we can use the generator.
    # But get_credential expects a session object.
    # We will grab a session just for this operation.
    async for db in get_db_session():
        token_data = await credential_service.get_credential(db, user_id, "google_calendar")
        if not token_data:
            raise ValueError("No Google Calendar credentials found. Please run /authgoogle in Telegram.")
            
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes')
        )
        
        return build('calendar', 'v3', credentials=creds)
    raise ValueError("Database connection failed.")

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
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
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
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def add_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    tool_context: ToolContext = None # ADK injects this
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
                'timeZone': 'UTC', # Assuming UTC for simplicity, in production infer from user
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return {"status": "success", "event_id": event.get('id'), "link": event.get('htmlLink')}

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
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return {"status": "success", "message": "Event deleted successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Re-implementations of previous placeholders using Calendar logic where appropriate

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
    # Construct RFC3339 timestamps
    start_dt = f"{date}T{time}:00Z"
    # Simple logic: 30 min duration
    # Need datetime parsing to add 30 mins, skipping for brevity, using string manipulation or assumtion
    # Let's use datetime module
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

async def get_task_list(tool_context: ToolContext, list_name: str = "default") -> Dict[str, Any]:
    """Placeholder for Task API."""
    return {"status": "info", "message": "TickTick/Task integration not yet authenticated."}

async def add_task(
    title: str, 
    tool_context: ToolContext, 
    description: str = "", 
    due_date: str = None
) -> Dict[str, Any]:
    """Placeholder for Task API."""
    return {"status": "info", "message": "TickTick/Task integration not yet authenticated."}
