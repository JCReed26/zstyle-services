import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent

def get_current_time() -> str:
    """Gets the current time

    Returns:
        A string with the current time.
    """
    tz = ZoneInfo('America/New_York')
    now = datetime.datetime.now(tz)
    return now.strftime('%Y-%m-%d %H:%M:%S %Z%z')


root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash-exp",
    description="A lifecoach and personal assistant",
    instruction="You are a helpful AI Life Coach and Personal assistant designed to be a friendly support through life events."
    "You have 3 sub_agents that relate to external pieces of software that interact with the users everyday life for example"
    "calendar_agent, gmail_agent, and gtasks_agent are all google workspace tools with specific ways to create entries"
    "when creating an entry ensure to get all the information you must collect first before prompting for anything else and try to fill in"
    "as many gaps as possible based upon the users input" \
    "you have 1 tools get_current_time which returns to you the current time",
    tools=[get_current_time],
    sub_agents=[]
)

print(f"DEBUG: Agent initialized with model: {root_agent.model}")
