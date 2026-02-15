"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

import os
import asyncio
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from copilotkit import CopilotKitMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.query import query_data
from src.todos import todo_tools, AgentState

client = MultiServerMCPClient({
    "copilotkit": {
        "transport": "http",
        "url": "https://mcp.copilotkit.ai",
    },
    "openmemory": {
        "transport": "http",
        "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
    },
})

mcp_tools = asyncio.run(client.get_tools())

model = ChatGoogleGenerativeAI(
    model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

agent = create_agent(
    model=model,
    tools=[query_data, *mcp_tools, *todo_tools],
    middleware=[CopilotKitMiddleware()],
    state_schema=AgentState,
    system_prompt=f"""
        You are a helpful assistant that helps users understand CopilotKit and LangGraph used together.

        When asked about generative UI:
        1. Ground yourself in relevant information from the CopilotKit documentation.
        2. Use one of the relevant tools to demonstrate that piece of generative UI.
        3. Explain the concept to the user with a brief summary.
    """
)

graph = agent
