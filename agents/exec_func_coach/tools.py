from google.adk.tools.agent_tool import AgentTool, AgentToolConfig
from google.adk.agents import Agent

# life integration tools 

# ticktick main life integration organization and life tracking
from services.ticktick.ticktick_service import TickTickService
ticktick_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='ticktick',
    description='TickTick Agent - helps users manage their life and tasks',
    instruction='You are a TickTick Agent - helps users manage their life and tasks',
    tools=[],
)
ticktick_agent_tool = AgentTool(ticktick_agent)
# google tools (calendar, tasks, gmail) through built in google adk tools
from google.adk.tools.google_api_tool import GoogleApiToolset

# Full tool list for exec_func_coach agent
tools = [

]

# FUTURE: apple tools