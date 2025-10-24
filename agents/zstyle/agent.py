import os
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .calendar_manager.agent import calendar_manager
from .email_manager.agent import email_manager

load_dotenv()

root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash-exp",
    description="A lifestyle focused personal assistant",
    instruction="""
    You are a personal assistant tasked with helping users handle managing their lives.
    You are focused on trying to get the user to have as little screentime as possible by 
    encouraging them to connect with reality. You have 2 agent who you can speak to that 
    the user cannot 
    """,
    tools=[
        AgentTool(calendar_manager),
        AgentTool(email_manager)
    ],
)

print(f"DEBUG: Agent initialized with model: {root_agent.model}")
