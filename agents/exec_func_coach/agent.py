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
from typing import Dict, Any, List, Optional
import datetime

from google.adk.agents import Agent
from google.adk.tools import ToolContext

from .helpers import (
    get_current_goal,
    set_current_goal,
    get_user_preferences,
    get_user_context,
    add_long_term_memory,
    search_long_term_memory,
    # OAuth initiation tools - URLs are logged, agent never sees tokens
    initiate_ticktick_auth,
    initiate_google_auth,
    check_ticktick_auth_status,
    check_google_auth_status,
)

from .capabilities import (
    google_calendar_tool,
    google_gmail_tool,
    google_search_tool,
    ticktick_tool,
)

from .prompt import ROOT_PROMPT


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


def get_default_tools() -> List[Any]:
    """
    Returns the list of tools enabled for the root agent.
    """
    tools = [
        # Memory tools
        get_current_goal,
        set_current_goal,
        get_user_preferences,
        get_user_context,
        # Long-term memory tools (OpenMemory)
        add_long_term_memory,
        search_long_term_memory,
        # OAuth initiation tools (URLs logged, not returned to agent)
        initiate_ticktick_auth,
        initiate_google_auth,
        check_ticktick_auth_status,
        check_google_auth_status,
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
    ]
    return [t for t in tools if t is not None]

def create_root_agent(
    model: str = 'gemini-2.0-flash-exp',
    tools: Optional[List[Any]] = None,
    sub_agents: Optional[List[Agent]] = None
) -> Agent:
    """
    Factory function to create the executive function coach agent.
    
    Args:
        model: The Gemini model to use.
        tools: List of tools to override defaults.
        sub_agents: List of sub-agents.
    """
    return Agent(
        model=model,
        name='exec_func_coach',
        description='Executive Function Personal Life Coach - helps users organize their life, track goals, and manage tasks.',
        instruction=ROOT_PROMPT,
        tools=tools if tools is not None else get_default_tools(),
        sub_agents=sub_agents if sub_agents is not None else [],
        # Sub-agents can be added here as the system grows
        # sub_agents=[planning_agent, habit_agent]
    )

# Define the executive function coach agent instance (singleton for default usage)
root_agent = create_root_agent()
