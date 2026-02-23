"""Executive Function Coach — orchestrator with A2A to personal_assistant and health_agent"""

import os
import asyncio
import json
from typing import TypedDict, Annotated, List, Union, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from langchain.agents import create_agent
from copilotkit import CopilotKitMiddleware

from src.state import VisionBoardState, Goal, Habit
from .prompt import EXEC_FUNC_COACH_PROMPT

LANGGRAPH_URL = os.environ.get("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")


# --- Tools ---

@tool
async def request_personal_assistant(task: str) -> str:
    """
    Send a task request to the Personal Assistant agent via A2A.
    Use for: email management, calendar scheduling, task management, automation config.
    The personal_assistant owns these capabilities — do not attempt them yourself.
    Args:
        task: Natural language description of what you need the Personal Assistant to do.
    """
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    # We use a throwaway thread for the sub-agent call or manage it otherwise
    # For simplicity, we just create a run
    result = await client.runs.create(
        thread_id=None,
        assistant_id="personal_assistant",
        input={"messages": [{"role": "user", "content": task}]},
    )
    return f"Personal Assistant completed task: {result}"


@tool
async def request_health_agent(task: str) -> str:
    """
    Send a task request to the Health Agent via A2A.
    Use for: workout plans, fitness stats, nutrition plans, Strava data.
    The health_agent owns these capabilities — do not attempt them yourself.
    Args:
        task: Natural language description of what you need the Health Agent to do.
    """
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    result = await client.runs.create(
        thread_id=None,
        assistant_id="health_agent",
        input={"messages": [{"role": "user", "content": task}]},
    )
    return f"Health Agent completed task: {result}"


@tool
def update_vision_board(goals: List[Goal], habits: List[Habit], lifestyle_theme: str = "My Lifestyle"):
    """
    Update the user's vision board (goals, habits, theme).
    Call this tool whenever you need to create, modify, or delete goals/habits or update the theme.
    """
    # This function is just for the tool definition/schema for the LLM.
    # The actual state update happens via CopilotKit state sync or handled by the middleware logic.
    return "Vision board updated."


async def get_mcp_tools():
    try:
        client = MultiServerMCPClient({
            "openmemory": {
                "transport": "http",
                "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
            },
        })
        return await client.get_tools()
    except Exception as e:
        print(f"Warning: OpenMemory MCP unavailable: {e}")
        return []


def create_exec_func_coach_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )
    
    mcp_tools = asyncio.run(get_mcp_tools())
    tools = [
        *mcp_tools,
        request_personal_assistant,
        request_health_agent,
        update_vision_board
    ]
    
    agent = create_agent(
        model=model,
        tools=tools,
        middleware=[CopilotKitMiddleware()],
        system_prompt=EXEC_FUNC_COACH_PROMPT,
    )
    
    return agent
