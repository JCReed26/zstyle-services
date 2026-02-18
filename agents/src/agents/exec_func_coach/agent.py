"""Executive Function Coach — orchestrator with A2A to personal_assistant and health_agent"""

import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from langchain.agents import create_agent
from copilotkit import CopilotKitMiddleware

from .prompt import EXEC_FUNC_COACH_PROMPT


LANGGRAPH_URL = os.environ.get("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")


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


def get_mcp_tools():
    client = MultiServerMCPClient({
        "openmemory": {
            "transport": "http",
            "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
        },
    })
    return asyncio.run(client.get_tools())


def create_exec_func_coach_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    tools = [
        *get_mcp_tools(),
        request_personal_assistant,
        request_health_agent,
    ]

    agent = create_agent(
        model=model,
        tools=tools,
        middleware=[CopilotKitMiddleware()],
        system_prompt=EXEC_FUNC_COACH_PROMPT,
    )

    return agent
