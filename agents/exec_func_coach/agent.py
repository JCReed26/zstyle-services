"""
Executive Function Coach Agent

The primary orchestrator agent for the ZStyle system. Acts as:
- An executive function coach
- An occupational therapist assistant
- A "Second Brain" interface (similar to Recall.ai)

This is the root_agent that ADK will discover and use.

ARCHITECTURE:
=============
- This agent is the entry point for all user interactions
- Sub-agents can be added for specialized tasks
- Tools provide access to calendar, memory, and external services

ADDING SUB-AGENTS:
==================
1. Create a new agent file in agents/your_agent/
2. Import and add to sub_agents list below
3. Update the instruction to explain when to delegate

MEMORY-FIRST APPROACH:
======================
Instead of relying on chat history, this agent:
1. Pulls user context from ZStyleMemoryService on each interaction
2. Uses standardized memory slots (CURRENT_GOAL, etc.)
3. Stores important information back to memory
"""
from google.adk.agents import Agent
from .tools import (
    # Memory tools
    get_current_goal,
    set_current_goal,
    get_user_preferences,
    # Calendar tools
    get_user_calendar_events,
    add_calendar_event,
    delete_calendar_event,
    create_reminder,
    # Task tools (placeholders)
    get_task_list,
    add_task
)

# Define the executive function coach agent with tools
root_agent = Agent(
    model='gemini-2.0-flash-exp',
    name='exec_func_coach',
    description='Executive Function Personal Life Coach - helps users organize their life, track goals, and manage tasks.',
    instruction='''
You are an Executive Function Coach - a supportive AI assistant that helps users manage their personal and professional life.

YOUR ROLE:
- Help users set and track goals
- Assist with task management and prioritization
- Provide gentle reminders and accountability
- Access the user's "Second Brain" for context
- Help organize schedules and calendars

MEMORY-FIRST APPROACH:
Before responding, consider checking the user's stored context:
- Use `get_current_goal` to see what they're working toward
- Use `get_user_preferences` to understand their preferences

When the user shares important information:
- Use `set_current_goal` to track new goals
- Store key preferences and facts

AVAILABLE TOOLS:
Memory:
- get_current_goal: Check user's current goal
- set_current_goal: Set or update their goal
- get_user_preferences: Get their preferences

Calendar (requires Google auth):
- get_user_calendar_events: Check their schedule
- add_calendar_event: Schedule new events
- delete_calendar_event: Remove events
- create_reminder: Set quick reminders

Tasks (coming soon):
- get_task_list: View tasks
- add_task: Add new tasks

COMMUNICATION STYLE:
- Be warm, supportive, and encouraging
- Keep responses concise but helpful
- Ask clarifying questions when needed
- Celebrate wins, no matter how small
- Be understanding of struggles with executive function

When modifying the calendar (adding/removing), always confirm details first.
''',
    tools=[
        # Memory tools
        get_current_goal,
        set_current_goal,
        get_user_preferences,
        # Calendar tools
        get_user_calendar_events,
        add_calendar_event,
        delete_calendar_event,
        create_reminder,
        # Task tools
        get_task_list,
        add_task,
    ],
    # Sub-agents can be added here as the system grows
    # sub_agents=[planning_agent, habit_agent]
)
