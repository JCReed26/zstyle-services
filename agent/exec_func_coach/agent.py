"""
Executive Function Coach Agent

This agent is a personal assistant that helps users manage online services
This agent will coach users to set and maintain systems that work for them to reach their goals.
This acts as the central agent for users in the zstyle system. Other agents will be able to interact if the user pays for it. This will be the central point for specialized agents to help each user reach their goals. The coach ... coaches users to buy the agents to assist in building optimal custom user systems and solutions.
"""
from google.adk.agents import Agent
from .prompt import EXEC_FUNC_COACH_PROMPT
from .tools import tools

# Define the executive function coach agent with tools
root_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='exec_func_coach',
    description='Executive Function Coach + Personal Assistant - helps users manage services online and coaches them to reach goals by building systems that work for them.',
    instruction=EXEC_FUNC_COACH_PROMPT,
    tools=tools,
)
