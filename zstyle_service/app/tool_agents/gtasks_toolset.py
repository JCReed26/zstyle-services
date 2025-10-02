import os
from dotenv import load_dotenv 

from google.adk.agents import Agent
from google.adk.tools.base_toolset import ToolPredicate
from google.adk.tools.google_api_tool.google_api_toolset import GoogleApiToolset

from typing import List
from typing import Optional
from typing import Union

load_dotenv()

host_client_id = os.getenv("GOOGLE_APIS_CLIENT_ID")
host_client_secret = os.getenv("GOOGLE_APIS_CLIENT_SECRET")

class GTasksToolset(GoogleApiToolset):
    """Auto-generated Tasks toolset based on Google Tasks API v1 spec exposed by Google API discovery API"""
    
    def __init__(
        self,
        client_id: str = None, 
        client_secret: str = None,
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
    ):
        super().__init__("tasks", "v1", client_id, client_secret, tool_filter)

# Agent implementation 
gtasks_agent = Agent(
    name="gtasks_agent",
    model="gemini-2.5-flash",
    instruction="""You are a helpful AI assistant that can manage Google Tasks.
    You can create, read, update, and delete tasks for the user.
    Your job is to help the user manage their tasks efficiently and effectively.
    """,
    tools=[GTasksToolset(
        client_id=host_client_id,
        client_secret=host_client_secret,
    )],
)