# googtools.py
"""
For google ecosystem tools

like calendar, gmail, tasks
"""

import logging
import asyncio
from typing import Optional, Dict
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.google_api_tool import GoogleApiToolset
from services import credential_service
from app.config import settings

logger = logging.getLogger(__name__)


# oauth helpers
async def get_google_credentials(user_id: str) -> Optional[Dict[str, str]]:
    """Get Google OAuth credentials for user."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return None
    
    creds = await credential_service.get_credentials(user_id, "google")
    if not creds:
        return None
    
    result = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "access_token": creds.get("token"),
    }
    if creds.get("refresh_token"):
        result["refresh_token"] = creds.get("refresh_token")
    return result


def get_google_credentials_sync(user_id: str) -> Optional[Dict[str, str]]:
    """Sync wrapper for Google credentials."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(get_google_credentials(user_id))
            except ImportError:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(get_google_credentials(user_id))
                finally:
                    new_loop.close()
        else:
            return loop.run_until_complete(get_google_credentials(user_id))
    except RuntimeError:
        return asyncio.run(get_google_credentials(user_id))


# other helpers
# (add any other Google-specific helpers here)


# get the tools
# Calendar Agent
google_calendar_toolset = None
google_calendar_agent = None
google_calendar_agent_tool = None

try:
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        google_calendar_toolset = GoogleApiToolset(
            api_name="calendar",
            api_version="v3",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        google_calendar_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='google_calendar',
            description='Google Calendar Agent - helps users manage their calendar events and schedules',
            instruction='You are a Google Calendar Agent. Help users view, create, update, and manage calendar events.',
            tools=[],
        )
        google_calendar_agent_tool = AgentTool(google_calendar_agent)
        logger.info("Google Calendar agent initialized successfully")
    else:
        logger.warning("Google OAuth not configured - Calendar agent unavailable")
except Exception as e:
    # This is expected if ADC is not configured - the toolset will use OAuth when needed
    logger.debug(f"Google Calendar toolset initialization note (will use OAuth when needed): {e}")
    google_calendar_toolset = None
    google_calendar_agent = None
    google_calendar_agent_tool = None


# Gmail Agent
google_gmail_toolset = None
google_gmail_agent = None
google_gmail_agent_tool = None

try:
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        google_gmail_toolset = GoogleApiToolset(
            api_name="gmail",
            api_version="v1",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        google_gmail_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='google_gmail',
            description='Google Gmail Agent - helps users manage their email',
            instruction='You are a Google Gmail Agent. Help users read, send, and manage emails.',
            tools=[],
        )
        google_gmail_agent_tool = AgentTool(google_gmail_agent)
        logger.info("Google Gmail agent initialized successfully")
    else:
        logger.warning("Google OAuth not configured - Gmail agent unavailable")
except Exception as e:
    # This is expected if ADC is not configured - the toolset will use OAuth when needed
    logger.debug(f"Google Gmail toolset initialization note (will use OAuth when needed): {e}")
    google_gmail_toolset = None
    google_gmail_agent = None
    google_gmail_agent_tool = None


# Tasks Agent
google_tasks_toolset = None
google_tasks_agent = None
google_tasks_agent_tool = None

try:
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        google_tasks_toolset = GoogleApiToolset(
            api_name="tasks",
            api_version="v1",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        google_tasks_agent = Agent(
            model='gemini-2.0-flash-exp',
            name='google_tasks',
            description='Google Tasks Agent - helps users manage their Google Tasks',
            instruction='You are a Google Tasks Agent. Help users create, update, and manage Google Tasks.',
            tools=[],
        )
        google_tasks_agent_tool = AgentTool(google_tasks_agent)
        logger.info("Google Tasks agent initialized successfully")
    else:
        logger.warning("Google OAuth not configured - Tasks agent unavailable")
except Exception as e:
    # This is expected if ADC is not configured - the toolset will use OAuth when needed
    logger.debug(f"Google Tasks toolset initialization note (will use OAuth when needed): {e}")
    google_tasks_toolset = None
    google_tasks_agent = None
    google_tasks_agent_tool = None


# search tool
google_search_agent = None
google_search_agent_tool = None

try:
    google_search_agent = Agent(
        model='gemini-2.0-flash-exp',
        name='search_web',
        description="Search the web for current information, facts, or context on any topic.",
        instruction='''You are a Google Search Agent specialized in finding accurate, up-to-date information from the web.

YOUR PURPOSE:
- Perform web searches when users need current information beyond training data
- Verify facts and gather context on topics
- Provide concise summaries with source citations
- Use search strategically - only search when information is needed

SEARCH STRATEGY:
1. Use clear, specific search queries that target the information needed
2. Focus on authoritative sources (official sites, reputable news, academic sources)
3. Summarize findings concisely - extract key facts and relevant details
4. Always cite sources using the grounding metadata provided
5. Include relevant URLs when available for user verification

WHEN TO SEARCH:
- Current events, recent news, or time-sensitive information
- Facts that may have changed since training data cutoff
- Verification of claims or statements
- Finding specific details, statistics, or data points
- Locating official documentation or authoritative sources

RESPONSE FORMAT:
- Start with a direct answer to the query
- Provide key facts and context
- Cite sources clearly: "According to [source]..." or "[Source] reports..."
- Include relevant URLs when provided in grounding metadata
- If multiple sources conflict, acknowledge the discrepancy
- If search yields no relevant results, state this clearly

GROUNDING METADATA:
- Use the grounding metadata provided with search results
- Include source URLs in your response when available
- Reference specific search queries used if helpful for transparency
- Acknowledge when information comes from search vs. your training data

IMPORTANT GUIDELINES:
- Do not search for information you already know from training
- Do not search for personal information or private data
- Respect rate limits - use search judiciously
- If a query is ambiguous, ask for clarification before searching
- Always verify information quality before presenting it''',
        tools=[google_search],
    )
    google_search_agent_tool = AgentTool(google_search_agent)
except Exception as e:
    logger.warning(f"Failed to initialize Google Search agent: {e}")