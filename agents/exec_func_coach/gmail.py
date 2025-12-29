"""
Gmail Organization Agent

Role: Manage inbox, create filters/labels, sort emails.
Auth: Multi-user OAuth via persistent credentials.
"""
import os
import contextvars
from typing import Optional, Dict, Any, List
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.google_api_tool.google_api_toolsets import GmailToolset

# Removed: from .helpers import _get_credential
# Removed: from database.models import CredentialType
# Agents never import credential helpers directly

# ContextVar for Gmail token injection
# Note: Google API Toolsets often expect env vars or credentials files.
# We need to bridge the persistent DB creds to the ADK toolset.
_current_gmail_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("gmail_token", default=None)


GMAIL_PROMPT = """
You are the Gmail Organization Specialist.
Your goal is to help the user achieve "Inbox Zero" and keep their email organized.

CAPABILITIES:
- List threads and messages
- Create and apply labels
- Create filters
- Draft replies
- Archive or trash emails

GUIDELINES:
- When organizing, prioritize unread messages from important contacts.
- Suggest creating filters for recurring newsletters or notifications.
- Always ask for confirmation before bulk archiving or deleting.
- Use the user's communication style when drafting replies.
"""

# Initialize Toolset
# In a real multi-user scenario, we might need to recreate this per request or patch the auth
# For ADK, we typically instantiate once.
google_gmail_toolset = GmailToolset(
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    tool_filter=None,
    service_account=None,
    tool_name_prefix='google_gmail_tools'
)

gmail_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='gmail_organizer',
    description='Specialist for Gmail organization and management.',
    instruction=GMAIL_PROMPT,
    tools=[google_gmail_toolset]
)


class GmailAgentTool(AgentTool):
    """
    Wrapper to handle multi-user authentication for Gmail.
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
             return {"status": "error", "message": "User not identified for Gmail access."}

        # Get token from AuthService (agents never see tokens directly)
        from services.auth import AuthService
        token = await AuthService.get_google_token(user_id)
        if not token:
             return {
                 "status": "error", 
                 "message": "Gmail authentication missing. Please authorize access."
             }
        
        # Inject token via ContextVar
        token_var = _current_gmail_token.set(token)
        
        try:
            return await super().run_async(tool_context, **kwargs)
        finally:
            _current_gmail_token.reset(token_var)

# Export wrapped tool
gmail_tool = GmailAgentTool(agent=gmail_agent)
