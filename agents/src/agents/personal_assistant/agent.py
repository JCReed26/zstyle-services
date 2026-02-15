"""Simple Connections Assistant chatbot"""

import os
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

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
        tools=[],  # No special tools yet
        system_prompt="""You are a Personal Assistant.
Help users maintain their connected tools and services."""
    )

    return agent
