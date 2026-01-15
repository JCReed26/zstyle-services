from google.adk.tools.agent_tool import AgentTool, AgentToolConfig
from google.adk.agents import Agent
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

# Initialize TickTickTool instance
ticktick_tool = TickTickTool()

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
    # Future: GoogleApiToolset tools
]

# FUTURE: apple tools