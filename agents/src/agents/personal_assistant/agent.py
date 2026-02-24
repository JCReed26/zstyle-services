"""Personal Assistant — supervisor over email_manager, calendar_agent, task_agent"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.graph import StateGraph, END
from copilotkit import CopilotKitMiddleware
from copilotkit.langgraph import CopilotKitState

from .prompt import PERSONAL_ASSISTANT_PROMPT, EMAIL_MANAGER_PROMPT, CALENDAR_AGENT_PROMPT, TASK_AGENT_PROMPT
from src.tools.state_tools import update_personal_assistant


class PersonalAssistantState(CopilotKitState):
    calendar: list
    emails: list
    tasks: list
    automations: list


def create_personal_assistant_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    try:
        from src.tools.gmail_tool import get_gmail_tools
        gmail_tools = get_gmail_tools()
    except Exception as e:
        print(f"Warning: Gmail tools unavailable: {e}")
        gmail_tools = []

    try:
        from src.tools.calendar_tool import get_calendar_tools
        calendar_tools = get_calendar_tools()
    except Exception as e:
        print(f"Warning: Calendar tools unavailable: {e}")
        calendar_tools = []

    # Provide update_personal_assistant tool to all sub-agents
    email_manager = create_agent(model=model, tools=gmail_tools + [update_personal_assistant], system_prompt=EMAIL_MANAGER_PROMPT, state_schema=CopilotKitState, middleware=[CopilotKitMiddleware()])
    calendar_agent = create_agent(model=model, tools=calendar_tools + [update_personal_assistant], system_prompt=CALENDAR_AGENT_PROMPT, state_schema=CopilotKitState, middleware=[CopilotKitMiddleware()])
    task_agent = create_agent(model=model, tools=[update_personal_assistant], system_prompt=TASK_AGENT_PROMPT, state_schema=CopilotKitState, middleware=[CopilotKitMiddleware()])

    def supervisor_router(state: PersonalAssistantState):
        if not state["messages"]:
            return "calendar_agent"

        last_msg = state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else last_msg.get("content", "")
        content = content.lower()

        if any(kw in content for kw in ["email", "gmail", "inbox", "send", "reply", "message"]):
            return "email_manager"
        if any(kw in content for kw in ["calendar", "schedule", "event", "block", "meeting", "week"]):
            return "calendar_agent"
        if any(kw in content for kw in ["task", "todo", "list", "reminder"]):
            return "task_agent"
        return "calendar_agent"

    graph = StateGraph(PersonalAssistantState)
    graph.add_node("supervisor", lambda state: state)
    graph.add_node("email_manager", email_manager)
    graph.add_node("calendar_agent", calendar_agent)
    graph.add_node("task_agent", task_agent)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", supervisor_router, {
        "email_manager": "email_manager",
        "calendar_agent": "calendar_agent",
        "task_agent": "task_agent",
    })
    graph.add_edge("email_manager", END)
    graph.add_edge("calendar_agent", END)
    graph.add_edge("task_agent", END)

    return graph.compile()
