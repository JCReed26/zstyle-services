import os
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.tools.google_api_tool import GoogleApiToolset

from google.oauth2 import service_account

# define mcp tools look at the docs 

load_dotenv()

# mcp for not 

# open api tools for a2a readable  

# i believe we need to change this to be the service account
CLIENT_ID=os.getenv("OAUTH2_CLIENT_ID")
CLIENT_SECRET=os.getenv("OAUTH2_CLIENT_SECRET")

service_account

google_calendar_toolset = GoogleApiToolset(
    api_name="calendar",
    api_version="v3",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

calendar_manager = LlmAgent(
    name="calendar_manager",
    description="agent to manage all the calendars and scheduling",
    model="gemini-2.0-flash",
    instruction="""you are a hightly skilled at one specific niche. taking
    everything from todo lists, meetings, lunches, etc on a users calendar""",
    tools=[google_calendar_toolset]
)