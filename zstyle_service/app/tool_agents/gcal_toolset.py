import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.google_api_tool.google_api_toolsets import CalendarToolset

load_dotenv()

host_client_id = os.getenv("GOOGLE_APIS_CLIENT_ID")
host_client_secret = os.getenv("GOOGLE_APIS_CLIENT_SECRET")

calendar_agent = Agent(
    name="calendar_agent",
    model="gemini-2.5-flash",
    instruction="""You are a helpful AI assistant that can manage Google Calendar.
    You can create, read, update, and delete calendar events for the user.
    Your job is to help the user manage their calendar efficiently and effectively.
    """,
    tools=[CalendarToolset(
        client_id=host_client_id,
        client_secret=host_client_secret,
    )],
)