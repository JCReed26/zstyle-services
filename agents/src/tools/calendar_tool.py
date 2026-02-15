import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_google_community import CalendarToolkit
from langchain_google_community.calendar.utils import (
    build_resource_service,
    get_google_credentials,
)

# Can review scopes here: https://developers.google.com/calendar/api/auth
# For instance, readonly scope is https://www.googleapis.com/auth/calendar.readonly
credentials = get_google_credentials(
    token_file="calendar_token.json",
    scopes=["https://www.googleapis.com/auth/calendar"],
    client_secrets_file="credentials.json",
)

api_resource = build_resource_service(credentials=credentials)
toolkit = CalendarToolkit(api_resource=api_resource)

def get_calendar_tools():
    return toolkit.get_tools()

prompt = """
You are a calendar assistant.
You are responsible for managing the users calendar.
You are able to create, update, and delete events in the users calendar.
You are able to search the users calendar for events.
You are able to get the users calendar events.

Use all tools available to you to complete the task.
"""

def get_calendar_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    agent = create_agent(
        model=model,
        tools=get_calendar_tools(),
        system_prompt=prompt,
    )
    return agent