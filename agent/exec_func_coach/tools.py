# tools.py
"""
Main tool registry for exec func coach

Combines all tools from googtools.py and ticktool.py
"""

import logging
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent

# Import Google tools
from agent.exec_func_coach.googtools import (
    google_calendar_agent_tool,
    google_gmail_agent_tool,
    google_tasks_agent_tool,
    google_search_agent_tool,
)

# Import TickTick tools
from agent.exec_func_coach.ticktool import (
    ticktick_tool,
    TICKTICK_PROMPT,
)

logger = logging.getLogger(__name__)


# TickTick Agent
ticktick_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='ticktick',
    description='TickTick Agent - helps users manage their life and tasks',
    instruction=TICKTICK_PROMPT,
    tools=[],
)
ticktick_agent_tool = AgentTool(ticktick_agent)


# Combine all tools
tools = [
    # TickTick tools
    ticktick_tool.add_task,
    ticktick_tool.get_tasks,
    ticktick_tool.update_task,
    ticktick_tool.delete_task,
    ticktick_tool.get_projects,
    
    # Google Search
    google_search_agent_tool,
    
    # Google API agents (calendar, gmail, tasks)
    google_calendar_agent_tool,
    google_gmail_agent_tool,
    google_tasks_agent_tool,
]

# Filter out None Tools (tools that fail to init)
# This handles: google_calendar_agent_tool, google_gmail_agent_tool, 
# google_tasks_agent_tool, and google_search_agent_tool if they fail to initialize
tools = [t for t in tools if t is not None]

# Log which tools are available
if logger.isEnabledFor(logging.DEBUG):
    available_tools = [getattr(t, '__name__', str(t)) for t in tools]
    logger.debug(f"Initialized {len(tools)} tools: {available_tools}")