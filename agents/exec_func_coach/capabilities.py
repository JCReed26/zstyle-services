import os
from dotenv import load_dotenv
from google.adk.tools.google_search_agent_tool import GoogleSearchAgentTool, create_google_search_agent
from google.adk.tools.google_api_tool.google_api_toolsets import CalendarToolset, GmailToolset

from services.memory import memory_service
from database.engine import AsyncSessionLocal
from database.models import Credential, CredentialType
from sqlalchemy import select
import asyncio

from mcp import StdioServerParameters
from google.adk.tools.mcp_tool import McpToolset

load_dotenv()
from google.adk.agents import Agent 
from google.adk.tools.agent_tool import AgentTool

# Import the specialized agent wrapper
from .ticktick import ticktick_tool_wrapper

# =============================================================================
# GOOGLE CALENDAR TOOL
# =============================================================================
google_calendar_toolset = CalendarToolset(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    tool_filter=None,
    service_account=None,
    tool_name_prefix='google_calendar_tools'
)
google_calendar_agent = Agent(
    name='google_calendar_agent',
    description='An agent that can manage a users google calendar',
    instruction='You are a google calendar agent that can manage a users google calendar',
    tools=[google_calendar_toolset]
)
google_calendar_tool = AgentTool(google_calendar_agent)

# =============================================================================
# GOOGLE GMAIL TOOL
# =============================================================================

google_gmail_toolset = GmailToolset(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    tool_filter=None,
    service_account=None,
    tool_name_prefix='google_gmail_tools'
)
google_gmail_agent = Agent(
    name='google_gmail_agent',
    description='An agent that can manage a users google gmail',
    instruction='You are a google gmail agent that can manage a users google gmail',
    tools=[google_gmail_toolset]
)
google_gmail_tool = AgentTool(google_gmail_agent)

# =============================================================================
# GOOGLE SEARCH TOOL
# =============================================================================

google_search_subagent = create_google_search_agent('gemini-2.0-flash-exp')
google_search_tool = GoogleSearchAgentTool(agent=google_search_subagent)

# =============================================================================
# TickTick Tool
# =============================================================================
# Aliasing the wrapper function as the tool
ticktick_tool = ticktick_tool_wrapper
