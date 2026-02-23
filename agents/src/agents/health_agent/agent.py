"""Health Agent — supervisor over fitness_coach and nutritionist sub-agents"""

import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from copilotkit import CopilotKitMiddleware
from copilotkit.langgraph import CopilotKitState

from .prompt import HEALTH_SYSTEM_PROMPT, FITNESS_COACH_PROMPT, NUTRITIONIST_PROMPT
from src.tools.state_tools import update_health


class HealthState(CopilotKitState):
    active_sub_agent: str
    fitness_plan: dict
    nutrition_plan: dict


def get_strava_tools():
    try:
        client = MultiServerMCPClient({
            "strava": {
                "transport": "http",
                "url": os.environ.get("STRAVA_MCP_URL", "http://localhost:8124/sse"),
            }
        })
        return asyncio.run(client.get_tools())
    except Exception as e:
        print(f"Warning: Strava MCP unavailable: {e}")
        return []


def create_health_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    strava_tools = get_strava_tools()
    
    # Provide update_health tool to sub-agents
    fitness_coach = create_agent(model=model, tools=strava_tools + [update_health], system_prompt=FITNESS_COACH_PROMPT, middleware=[CopilotKitMiddleware()], state_schema=CopilotKitState)
    nutritionist = create_agent(model=model, tools=[update_health], system_prompt=NUTRITIONIST_PROMPT, middleware=[CopilotKitMiddleware()], state_schema=CopilotKitState)

    def supervisor_router(state: HealthState):
        if not state["messages"]:
            return "fitness_coach"
            
        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")
        content = content.lower()
        
        if any(kw in content for kw in ["meal", "diet", "nutrition", "food", "recipe", "eat"]):
            return "nutritionist"
        return "fitness_coach"  # default

    graph = StateGraph(HealthState)
    graph.add_node("supervisor", lambda state: state)
    graph.add_node("fitness_coach", fitness_coach)
    graph.add_node("nutritionist", nutritionist)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", supervisor_router, {
        "fitness_coach": "fitness_coach",
        "nutritionist": "nutritionist",
    })
    graph.add_edge("fitness_coach", END)
    graph.add_edge("nutritionist", END)

    return graph.compile()
