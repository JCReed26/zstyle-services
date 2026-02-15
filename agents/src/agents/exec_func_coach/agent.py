"""Simple Executive Function Coach chatbot"""

import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from copilotkit import CopilotKitMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

def create_exec_func_coach_agent():
    """Simple chatbot with OpenMemory for persistent context"""

    # Connect to OpenMemory MCP
    client = MultiServerMCPClient({
        "openmemory": {
            "transport": "http",
            "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
        },
    })
    mcp_tools = asyncio.run(client.get_tools())

    # Initialize LLM
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    # Simple chatbot
    agent = create_agent(
        model=model,
        tools=mcp_tools,  # Only OpenMemory tools
        middleware=[CopilotKitMiddleware()],
        system_prompt="""You are an Executive Function Coach assistant.
Help users with task management, organization, and breaking down complex tasks into manageable steps."""
    )

    return agent
