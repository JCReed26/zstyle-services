from google.adk.agents import Agent 
from google.adk.tools.google_search import google_search
from .tools import get_user_calendar_events, add_calendar_event, delete_calendar_event, create_reminder

# TODO: add agent to manage google calendar, ticktick, and other todo tools 
google_calendar_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='google_calendar_agent',
    description='A agent that can manage google calendar',
    instruction='You are a google calendar agent that can manage google calendar',
    tools=[get_user_calendar_events, add_calendar_event, delete_calendar_event, create_reminder],
)

# TODO: add agent to help with email management and inbox zero 

# TODO: add agent for helping create and plan goals and manage routine the specialist
# This is the occupational therapist assistant agent that helps the executive function coach agent
# This is where special functions will be handled for creating SYSTEMS for people not just lists
