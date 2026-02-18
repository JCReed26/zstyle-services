"""Personal Assistant chatbot & Agentic Agent

This agent is a personal assistant to be triggered by the exec_func_coach agent.
This agent controls multiple sub-agents each representing a different tool or service integrated.
This agent is responsible for creating and delegating tasks to the sub-agents to complete the request.

It is designed to handle all day to day productivity apps for the user. (Calendar, Email, Tasks, etc.)
The goal is a custom sync across all apps for the user.
"""

import asyncio
import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient

# TODO: Fix calendar tool - build_resource_service API changed
# from src.tools.calendar_tool import get_calendar_tools
from .prompt import prompt

# Calendar Tools is also available as an agent for now we will use the tool directly

def get_mcp_tools():
    """Get MCP Tools for agent"""
    client = MultiServerMCPClient({
        "openmemory": {
            "transport": "http",
            "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
        },
    })
    return asyncio.run(client.get_tools())

def create_personal_assistant_agent():
    """Simple chatbot for managing connected tools"""

    # Initialize LLM (no MCP connection)
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    # Simple chatbot
    agent = create_agent(
        model=model,
        tools=[*get_mcp_tools()],  # TODO: Add back calendar tools when API fixed
        system_prompt=prompt,
    )

    return agent
