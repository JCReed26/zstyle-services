"""
For google ecosystem tools

like calendar, gmail, tasks
"""

import logging
import os
import asyncio
from typing import Optional, Dict, List, Callable
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.google_api_tool.google_api_toolsets import (
    CalendarToolset,
    GmailToolset,
    # Note: Tasks API may not be in google_api_toolsets.py
    # If not available, we'll use GoogleApiToolset directly
)
from google.adk.tools.google_api_tool import GoogleApiToolset
from google.adk.auth.auth_credential import ServiceAccount
from services.credential_service import credential_service
from app.config import settings

logger = logging.getLogger(__name__)

# Check if Google tools integration is enabled
INTEGRATE_GOOGLE_TOOLS = os.getenv("INTEGRATE_GOOGLE_TOOLS", "true").lower() == "true"

# Check if we're in telegram-bot container (uses HTTP bridge, no ADC needed)
IS_TELEGRAM_BOT_CONTAINER = os.getenv("AGENT_URL") is not None


# OAuth helpers
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


def create_user_credential_callback(user_id: str) -> Optional[Callable]:
    """
    Create a credential callback function for per-user OAuth.
    
    This callback will be called by the toolset when it needs credentials
    for a specific user. The toolset will use this to refresh tokens as needed.
    """
    def credential_callback():
        """Callback to get user credentials."""
        creds = get_google_credentials_sync(user_id)
        if not creds:
            return None
        
        # Return credentials in format expected by GoogleApiToolset
        # The toolset will handle token refresh using refresh_token
        return {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "access_token": creds.get("access_token"),
            "refresh_token": creds.get("refresh_token"),
        }
    
    return credential_callback if get_google_credentials_sync(user_id) else None

def create_toolset_with_user_auth(
    toolset_class,
    user_id: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Optional[object]:
    """
    Create a Google API toolset with per-user OAuth authentication.
    
    Args:
        toolset_class: The toolset class (e.g., CalendarToolset)
        user_id: User ID for OAuth credentials
        client_id: OAuth client ID (from settings if None)
        client_secret: OAuth client secret (from settings if None)
    
    Returns:
        Toolset instance or None if credentials unavailable
    """
    if not INTEGRATE_GOOGLE_TOOLS:
        logger.debug("Google tools integration disabled")
        return None
    
    client_id = client_id or settings.GOOGLE_CLIENT_ID
    client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
    
    if not client_id or not client_secret:
        logger.debug("Google OAuth not configured")
        return None
    
    try:
        # Check if user has credentials
        user_creds = get_google_credentials_sync(user_id)
        if not user_creds:
            logger.debug(f"User {user_id} has no Google credentials")
            return None
        
        # Create toolset with OAuth credentials
        # The toolset will use these for authentication
        toolset = toolset_class(
            client_id=client_id,
            client_secret=client_secret,
            # Note: GoogleApiToolset may need access_token/refresh_token
            # passed differently - this depends on ADK implementation
        )
        
        return toolset
    except Exception as e:
        logger.warning(f"Failed to create toolset for user {user_id}: {e}")
        return None


# DEPRECATED: Module-level toolset initialization removed
# ============================================================
# REASON: This pattern violates ADK credential management patterns.
# Toolsets initialized at module load cannot access per-user credentials
# stored in the database. ADK expects credentials to flow through
# ToolContext using request_credential() and get_auth_response().
#
# See Phase 2 rebuild: Custom Google API tools will be created that
# retrieve credentials per-request from the database (similar to TickTick pattern).
#
# OLD CODE (BROKEN):
# google_calendar_toolset = CalendarToolset(
#     client_id=settings.GOOGLE_CLIENT_ID,
#     client_secret=settings.GOOGLE_CLIENT_SECRET,
# )
# ============================================================

google_calendar_toolset = None
google_calendar_agent = None
google_calendar_agent_tool = None

google_gmail_toolset = None
google_gmail_agent = None
google_gmail_agent_tool = None

google_tasks_toolset = None
google_tasks_agent = None
google_tasks_agent_tool = None

# PHASE 2: Module-level initialization disabled
# Custom Google API tools will be created per-request with user credentials
# See: agent/exec_func_coach/google_api_tools.py (to be created)
if False and INTEGRATE_GOOGLE_TOOLS and not IS_TELEGRAM_BOT_CONTAINER:
    try:
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            # Initialize Calendar toolset
            google_calendar_toolset = CalendarToolset(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            
            # Pass toolset directly to agent - ADK handles tool extraction at runtime
            google_calendar_agent = Agent(
                model='gemini-2.0-flash-exp',
                name='google_calendar',
                description='Google Calendar Agent - helps users manage their calendar events and schedules',
                instruction='You are a Google Calendar Agent. Help users view, create, update, and manage calendar events.',
                tools=[google_calendar_toolset],
            )
            google_calendar_agent_tool = AgentTool(google_calendar_agent)
            logger.info("Google Calendar agent initialized successfully")
        else:
            logger.warning("Google OAuth not configured - Calendar agent unavailable")
    except Exception as e:
        logger.warning(f"Failed to initialize Google Calendar toolset: {e}", exc_info=True)
        google_calendar_toolset = None
        google_calendar_agent = None
        google_calendar_agent_tool = None

    try:
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            # Initialize Gmail toolset
            google_gmail_toolset = GmailToolset(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            
            # Pass toolset directly to agent - ADK handles tool extraction at runtime
            google_gmail_agent = Agent(
                model='gemini-2.0-flash-exp',
                name='google_gmail',
                description='Google Gmail Agent - helps users manage their email',
                instruction='You are a Google Gmail Agent. Help users read, send, and manage emails.',
                tools=[google_gmail_toolset],
            )
            google_gmail_agent_tool = AgentTool(google_gmail_agent)
            logger.info("Google Gmail agent initialized successfully")
        else:
            logger.warning("Google OAuth not configured - Gmail agent unavailable")
    except Exception as e:
        logger.warning(f"Failed to initialize Google Gmail toolset: {e}", exc_info=True)
        google_gmail_toolset = None
        google_gmail_agent = None
        google_gmail_agent_tool = None

    try:
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            # Initialize Tasks toolset (using GoogleApiToolset directly if TasksToolset doesn't exist)
            google_tasks_toolset = GoogleApiToolset(
                api_name="tasks",
                api_version="v1",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            
            # Pass toolset directly to agent - ADK handles tool extraction at runtime
            google_tasks_agent = Agent(
                model='gemini-2.0-flash-exp',
                name='google_tasks',
                description='Google Tasks Agent - helps users manage their Google Tasks',
                instruction='You are a Google Tasks Agent. Help users create, update, and manage Google Tasks.',
                tools=[google_tasks_toolset],
            )
            google_tasks_agent_tool = AgentTool(google_tasks_agent)
            logger.info("Google Tasks agent initialized successfully")
        else:
            logger.warning("Google OAuth not configured - Tasks agent unavailable")
    except Exception as e:
        logger.warning(f"Failed to initialize Google Tasks toolset: {e}", exc_info=True)
        google_tasks_toolset = None
        google_tasks_agent = None
        google_tasks_agent_tool = None
elif IS_TELEGRAM_BOT_CONTAINER:
    logger.info("Skipping Google tools initialization in telegram-bot container (uses HTTP bridge)")
else:
    logger.info("Google tools integration disabled via INTEGRATE_GOOGLE_TOOLS environment variable")


# Search tool (doesn't require OAuth)
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
    logger.warning(f"Failed to initialize Google Search agent: {e}", exc_info=True)