import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.google_api_tool import GmailToolset

load_dotenv()

host_client_id = os.getenv("GOOGLE_APIS_CLIENT_ID")
host_client_secret = os.getenv("GOOGLE_APIS_CLIENT_SECRET")

gmail_agent = Agent(
    name="gmail_agent",
    model="gemini-2.5-flash",
    instruction="""You are a helpful AI assistant that can manage Gmail.
    You can read, send, and organize emails for the user.
    Your job is to help the user manage their email efficiently and effectively.
    """,
    tools=[GmailToolset(
        client_id=host_client_id,
        client_secret=host_client_secret,
    )],
)