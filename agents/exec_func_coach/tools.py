from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent
from google.adk.tools import google_search
import asyncio
import logging
from typing import Optional, Dict, Any

# life integration tools 

# ticktick main life integration organization and life tracking
from services.ticktick.ticktick_service import TickTickService
from tools.ticktick_tool import TickTickTool

ticktick_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='ticktick',
    description='TickTick Agent - helps users manage their life and tasks',
    instruction='You are a TickTick Agent - helps users manage their life and tasks',
    tools=[],
)
ticktick_agent_tool = AgentTool(ticktick_agent)

# Google Search Agent - dedicated agent for web search with grounding
google_search_agent = Agent(
    model='gemini-2.0-flash-exp',  # Gemini 2 required for search grounding
    name='search_web',
    description="Search the web for current information, facts, or context on any topic. Use this when you need up-to-date information that isn't in your training data, when you need to verify facts, or when you need to find specific details, statistics, or authoritative sources. The search results include grounding metadata with source citations and URLs.",
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
    tools=[google_search],  # Single tool - required for proper grounding
)

# Wrap Google Search agent as AgentTool for use by main agent
# Note: AgentTool uses the agent's name and description automatically
google_search_agent_tool = AgentTool(google_search_agent)

# Initialize TickTickTool instance
# #region debug log
try:
    import json, time, os
    log_path = '/tmp/debug.log'
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"tools.py:23","message":"Before TickTickTool instantiation","data":{},"timestamp":int(time.time()*1000)})+'\n')
except: pass
# #endregion
ticktick_tool = TickTickTool()
# #region debug log
try:
    import json, time
    with open('/tmp/debug.log', 'a') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"tools.py:24","message":"After TickTickTool instantiation","data":{},"timestamp":int(time.time()*1000)})+'\n')
except: pass
# #endregion

# google tools (calendar, tasks, gmail) through built in google adk tools
from google.adk.tools.google_api_tool import GoogleApiToolset

# Import credential service and settings
from services import credential_service
from core.config import settings

logger = logging.getLogger(__name__)


async def get_google_credentials(user_id: str) -> Optional[Dict[str, str]]:
    """
    Dynamic credential provider for GoogleApiToolset.
    
    Fetches user-specific OAuth tokens from credential_service and combines
    them with application-level client credentials from environment variables.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with Google OAuth credentials, or None if credentials don't exist
        Format: {
            "client_id": "...",
            "client_secret": "...",
            "access_token": "...",
            "refresh_token": "..."
        }
    """
    # Check if client credentials are configured
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.warning(
            "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured. "
            "Google OAuth features will not work."
        )
        return None
    
    # Fetch user-specific tokens
    creds = await credential_service.get_credentials(user_id, "google")
    
    if not creds:
        # No credentials for this user - return None to trigger OAuth flow
        return None
    
    # Map credential service format to GoogleApiToolset format
    result: Dict[str, str] = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "access_token": creds.get("token"),  # Map token -> access_token
    }
    
    # Add refresh_token if present
    if creds.get("refresh_token"):
        result["refresh_token"] = creds["refresh_token"]
    
    return result


def get_google_credentials_sync(user_id: str) -> Optional[Dict[str, str]]:
    """
    Synchronous wrapper for get_google_credentials.
    
    GoogleApiToolset may require a synchronous credential provider.
    This wrapper bridges the async credential_service to sync.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with Google OAuth credentials, or None
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we're in an async context
            # Use nest_asyncio if available, otherwise create new loop
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(get_google_credentials(user_id))
            except ImportError:
                # nest_asyncio not available, create new event loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(get_google_credentials(user_id))
                finally:
                    new_loop.close()
        else:
            # Loop exists but not running
            return loop.run_until_complete(get_google_credentials(user_id))
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(get_google_credentials(user_id))


# Initialize GoogleApiToolset
# Note: GoogleApiToolset requires api_name and api_version
# For now, we'll create toolsets for common Google APIs
# Credentials will be handled per-user through the context or OAuth flow
google_toolsets = []

# Common Google APIs to enable
GOOGLE_APIS = [
    ("calendar", "v3"),
    ("gmail", "v1"),
    ("tasks", "v1"),
]

try:
    # Initialize toolsets for each Google API
    # Client credentials from env, user tokens handled per-request
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        for api_name, api_version in GOOGLE_APIS:
            try:
                toolset = GoogleApiToolset(
                    api_name=api_name,
                    api_version=api_version,
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET,
                )
                google_toolsets.append(toolset)
            except Exception as e:
                logger.warning(f"Failed to initialize GoogleApiToolset for {api_name}: {e}")
        
        # For backward compatibility, expose first toolset as google_toolset
        google_toolset = google_toolsets[0] if google_toolsets else None
    else:
        logger.warning(
            "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured. "
            "Google tools will not be available until OAuth is configured."
        )
        google_toolset = None
except Exception as e:
    # Log error but allow initialization to continue
    logger.warning(f"Failed to initialize GoogleApiToolset: {e}")
    logger.warning("Google tools will not be available until OAuth is configured.")
    google_toolset = None
    google_toolsets = []

# Full tool list for exec_func_coach agent
tools = [
    ticktick_tool.add_task,
    ticktick_tool.get_tasks,
    google_search_agent_tool,  # Google Search agent with grounding
    # Future: GoogleApiToolset tools
]

# FUTURE: apple tools