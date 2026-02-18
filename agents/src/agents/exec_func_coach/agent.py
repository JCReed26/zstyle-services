"""Simple Executive Function Coach chatbot"""

import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from copilotkit import CopilotKitMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

from .prompt import prompt

def get_mcp_tools():
    """Get MCP Tools for agent"""
    client = MultiServerMCPClient({
        "openmemory": {
            "transport": "http",
            "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
        },
    })
    return asyncio.run(client.get_tools())

def create_exec_func_coach_agent():
    """Simple chatbot with OpenMemory for persistent context"""

    # Initialize LLM
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    # Simple chatbot
    agent = create_agent(
        model=model,
        tools=[*get_mcp_tools()],  # Only OpenMemory tools
        middleware=[CopilotKitMiddleware()],
        system_prompt=prompt,
    )

    return agent
