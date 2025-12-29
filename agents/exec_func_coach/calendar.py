"""
Calendar Scheduler Agent

Role: Reschedule events, find time slots, move conflicts.
Auth: Multi-user OAuth via persistent credentials.
"""
import os
import contextvars
from typing import Optional, Dict, Any
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_api_tool.google_api_toolsets import CalendarToolset

# Removed: from .helpers import _get_credential
# Removed: from database.models import CredentialType
# Agents never import credential helpers directly

# ContextVar for Calendar token injection
_current_calendar_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("calendar_token", default=None)

CALENDAR_PROMPT = """
You are the Calendar Scheduler Specialist.
Your goal is to optimize the user's schedule, resolve conflicts, and find free time.

CAPABILITIES:
- List events and calendars
- Create, update, delete events
- Find free/busy time

GUIDELINES:
- When rescheduling, explain WHY the new time is better (e.g., "Moved to 2 PM to give you a lunch break").
- Avoid scheduling over existing conflicts unless explicitly asked.
- If multiple time slots are available, offer 2-3 options.
- Handle timezone conversions carefully.
"""

# Initialize Toolset
google_calendar_toolset = CalendarToolset(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    tool_filter=None,
    service_account=None,
    tool_name_prefix='google_calendar_tools'
)

calendar_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='calendar_scheduler',
    description='Specialist for Calendar scheduling and time management.',
    instruction=CALENDAR_PROMPT,
    tools=[google_calendar_toolset]
)

class CalendarAgentTool(AgentTool):
    """
    Wrapper to handle multi-user authentication for Calendar.
    """
    def __init__(self, agent: Agent):
        super().__init__(agent=agent)
    
    async def run_async(self, tool_context: ToolContext, **kwargs) -> Dict[str, Any]:
        user_id = tool_context.state.get('user_id') if tool_context.state else None
        if not user_id:
            # Fallback to ContextVar
            from channels.router import _current_user_id
            user_id = _current_user_id.get()
        if not user_id:
             return {"status": "error", "message": "User not identified for Calendar access."}

        # Get token from AuthService (agents never see tokens directly)
        from services.auth import AuthService
        token = await AuthService.get_google_token(user_id)
        if not token:
             return {
                 "status": "error", 
                 "message": "Calendar authentication missing. Please authorize access."
             }
        
        # Inject token via ContextVar
        token_var = _current_calendar_token.set(token)
        
        try:
            return await super().run_async(tool_context, **kwargs)
        finally:
            _current_calendar_token.reset(token_var)

# Export wrapped tool
calendar_tool = CalendarAgentTool(agent=calendar_agent)

