"""
Executive Function Coach Agent

The primary orchestrator agent for the ZStyle system. Acts as:
- An executive function coach
- An occupational therapist assistant
- A "Second Brain" interface (similar to Recall.ai)

This is the root_agent that ADK will discover and use.

ARCHITECTURE:
=============
- This agent is the entry point for all user interactions
- Sub-agents can be added for specialized tasks
- Tools provide access to calendar, memory, and external services

ADDING SUB-AGENTS:
==================
1. Create a new agent file in agents/your_agent/
2. Import and add to sub_agents list below
3. Update the instruction to explain when to delegate

MEMORY-FIRST APPROACH:
======================
Instead of relying on chat history, this agent:
1. Pulls user context from ZStyleMemoryService on each interaction
2. Uses standardized memory slots (CURRENT_GOAL, etc.)
3. Stores important information back to memory
"""
from google.adk.agents import Agent

from .helpers import (
    get_current_goal,
    set_current_goal,
    get_user_preferences,
    get_user_context,
)

from .capabilities import (
    google_calendar_tool,
    google_gmail_tool,
    google_search_tool,
    ticktick_tool,
)

from google.adk.tools import ToolContext
from .prompt import ROOT_PROMPT
from typing import Dict, Any
import datetime

# =============================================================================
# DATE TOOLS
# =============================================================================

async def get_todays_date(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current date.
    """
    return {"status": "success", "date": datetime.datetime.now().strftime("%Y-%m-%d")}

async def get_day_of_week(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current day of the week.
    """
    return {"status": "success", "day_of_week": datetime.datetime.now().strftime("%A")}

async def get_month(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current month.
    """
    return {"status": "success", "month": datetime.datetime.now().strftime("%B")}

async def get_year(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current year.
    """
    return {"status": "success", "year": datetime.datetime.now().strftime("%Y")}

async def get_time(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current time.
    """
    return {"status": "success", "time": datetime.datetime.now().strftime("%H:%M:%S")}

async def get_timezone(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current timezone.
    """
    return {"status": "success", "timezone": datetime.datetime.now().strftime("%Z")}


# Define the executive function coach agent with tools
root_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='exec_func_coach',
    description='Executive Function Personal Life Coach - helps users organize their life, track goals, and manage tasks.',
    instruction=ROOT_PROMPT,
    tools=[
        # Memory tools
        get_current_goal,
        set_current_goal,
        get_user_preferences,
        get_user_context,
        # Google Workspace tools
        google_calendar_tool,
        google_gmail_tool,  
        ticktick_tool,
        # Date tools
        get_todays_date,
        get_day_of_week,
        get_month,
        get_year,
        get_time,
        get_timezone,
        # google search 
        google_search_tool,
    ],
    # Sub-agents can be added here as the system grows
    # sub_agents=[planning_agent, habit_agent]
)
