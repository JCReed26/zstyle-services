"""
Orchestrator Agent - Executive Function Coach

This agent acts as the central router and coordinator.
It analyzes user intent and delegates to specialized sub-agents.
"""
from typing import List, Optional
from google.adk.agents import Agent
from google.adk.tools import ToolContext

# Import Sub-Agents (We will implement these one by one)
# For now, we import what we have or placeholder
from .ticktick import ticktick_agent

# Placeholder for future agents
# from .gmail import gmail_agent
# from .calendar import calendar_agent
# from .memory import memory_specialist_agent

ORCHESTRATOR_PROMPT = """
You are the Executive Function Coach Orchestrator.
Your goal is to help the user manage their life by coordinating specialized sub-agents.

CORE RESPONSIBILITIES:
1. Analyze User Intent: Determine what the user wants to do (e.g., check email, schedule meeting, remember something).
2. Delegate to Sub-Agents: Pass the request to the most appropriate specialist.
3. Synthesize Responses: Provide a unified, helpful response to the user.

AVAILABLE SPECIALISTS:
- TickTick Manager: For all task management (add task, check list, complete task).
- [Future] Gmail Organizer: For email management.
- [Future] Calendar Scheduler: For calendar management.
- [Future] Memory Specialist: For long-term memory storage/retrieval.

GUIDELINES:
- If a user asks to "remind me to buy milk", delegate to TickTick Manager.
- If a user asks "what did I do yesterday?", check Memory Specialist (once available).
- If a request involves multiple domains (e.g., "Email John to meet tomorrow"), break it down or ask clarifying questions.
- Always maintain a supportive, coaching tone.
"""

def create_orchestrator_agent(
    model: str = 'gemini-2.0-flash-exp',
    sub_agents: Optional[List[Agent]] = None
) -> Agent:
    """
    Factory function to create the orchestrator agent.
    """
    # Default sub-agents list
    if sub_agents is None:
        sub_agents = [
            ticktick_agent,
            # Add others as they are implemented
        ]
        
    return Agent(
        model=model,
        name='orchestrator',
        description='Executive Function Coach - Orchestrates specialized agents.',
        instruction=ORCHESTRATOR_PROMPT,
        sub_agents=sub_agents,
        tools=[] # The orchestrator mainly routes, tools are on sub-agents
    )

# Singleton instance
orchestrator_agent = create_orchestrator_agent()
