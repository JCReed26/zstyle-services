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

from .helpers import _get_credential
from database.models import CredentialType

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

        # 1. Retrieve Credential
        cred = await _get_credential(user_id, CredentialType.GOOGLE_OAUTH)
        if not cred:
             return {
                 "status": "error", 
                 "message": "Gmail authentication missing. Please authorize access."
             }
        
        # 2. Inject Credential
        # The ADK Gmail toolset might look for credentials in specific places.
        # This implementation depends heavily on how GmailToolset consumes auth.
        # If it uses google-auth library, we might need to construct a Credentials object
        # and monkey-patch or pass it.
        
        # For this implementation, we will assume a mechanism similar to TickTick
        # or that we can pass the token. Since GmailToolset is a wrapper,
        # we might need to rely on the environment or a custom credentials provider.
        
        # TODO: Implement robust token injection for Google tools. 
        # For now, we set the context var which can be used by a custom auth provider.
        token = _current_gmail_token.set(cred.get('token'))
        
        try:
            return await super().run_async(tool_context, **kwargs)
        finally:
            _current_gmail_token.reset(token)

# Export wrapped tool
gmail_tool = GmailAgentTool(agent=gmail_agent)
