from google.adk.agents import Agent 
from google.adk.tools.google_search_tool import google_search


root_agent = Agent(
    name="sample_search_agent",
    model="gemini-2.0-flash-live-001",
    description="simple search agent who acts as a friend",
    instruction="you are a helpful chat agent to talk to like a friend with the ability to search google",
    tools=[google_search]
)