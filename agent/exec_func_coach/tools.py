# tools.py
"""
Main tool registry for exec func coach

Combines all tools from googtools.py and ticktool.py
"""

import logging
import datetime
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent

# Import Google tools
# PHASE 2: Using custom Google API tools instead of broken ADK toolsets
from agent.exec_func_coach.google_api_tools import (
    get_calendar_events,
    create_calendar_event,
)
# Google Search doesn't require OAuth, so it still works
from agent.exec_func_coach.googtools import google_search_agent_tool

# Import TickTick tools
from agent.exec_func_coach.ticktool import (
    add_task,
    get_tasks,
    update_task,
    delete_task,
    get_projects,
    TICKTICK_PROMPT,
)

logger = logging.getLogger(__name__)


# TickTick Agent
# Note: TickTick tools are registered directly as functions (below) for immediate use.
# The agent wrapper is kept for consistency and potential future use by the root agent.
ticktick_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='ticktick',
    description='TickTick Agent - helps users manage their life and tasks',
    instruction=TICKTICK_PROMPT,
    tools=[add_task, get_tasks, update_task, delete_task, get_projects],
)
ticktick_agent_tool = AgentTool(ticktick_agent)

def date_tool():
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Combine all tools
tools = [
    # TickTick tools (wrapper functions that inject user_id from context)
    add_task,
    get_tasks,
    update_task,
    delete_task,
    get_projects,
    
    # Google Search (doesn't require OAuth)
    google_search_agent_tool,
    
    # Google API tools (custom implementation with per-user credentials)
    get_calendar_events,
    create_calendar_event,
    # TODO: Add more Google API tools (Gmail, Tasks) following same pattern

    # quick-helpers
    date_tool
]

# Filter out None Tools (tools that fail to init)
# This handles: google_calendar_agent_tool, google_gmail_agent_tool, 
# google_tasks_agent_tool, and google_search_agent_tool if they fail to initialize
tools = [t for t in tools if t is not None]

# Log which tools are available
if logger.isEnabledFor(logging.DEBUG):
    available_tools = [getattr(t, '__name__', str(t)) for t in tools]
    logger.debug(f"Initialized {len(tools)} tools: {available_tools}")