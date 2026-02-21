"""Health Agent — supervisor over fitness_coach and nutritionist sub-agents"""

import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from typing import TypedDict, Annotated
import operator

from .prompt import HEALTH_SYSTEM_PROMPT, FITNESS_COACH_PROMPT, NUTRITIONIST_PROMPT


class HealthState(TypedDict):
    messages: Annotated[list, operator.add]
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
    fitness_coach = create_agent(model=model, tools=strava_tools, system_prompt=FITNESS_COACH_PROMPT)
    nutritionist = create_agent(model=model, tools=[], system_prompt=NUTRITIONIST_PROMPT)

    def supervisor_router(state: HealthState):
        last_msg = state["messages"][-1].content.lower() if state["messages"] else ""
        if any(kw in last_msg for kw in ["meal", "diet", "nutrition", "food", "recipe", "eat"]):
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
