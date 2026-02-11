from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.exec_func_coach.state import AgentState
from app.agents.exec_func_coach.prompts import SYSTEM_PROMPT
from app.agents.exec_func_coach.tools import tools
from app.core.memory import memory_manager

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)

def retrieve_context(state: AgentState) -> AgentState:
    last_message = state["messages"][-1].content if state["messages"] else ""
    state["context"] = memory_manager.get_context(state["user_id"], last_message)
    return state

def generate_response(state: AgentState) -> AgentState:
    context_str = "\n".join(state["context"]) if state["context"] else "No prior context"
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(context=context_str))] + list(state["messages"])
    response = llm.invoke(messages)
    state["messages"] = state["messages"] + [response]
    return state

def save_to_memory(state: AgentState) -> AgentState:
    messages = state["messages"]
    user_message = messages[-2].content if len(messages) >= 2 else ""
    assistant_response = messages[-1].content if messages else ""
    if user_message and assistant_response:
        memory_manager.save_interaction(state["user_id"], user_message, assistant_response)
    return state

workflow = StateGraph(AgentState)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_response", generate_response)
workflow.add_node("save_to_memory", save_to_memory)
workflow.set_entry_point("retrieve_context")
workflow.add_edge("retrieve_context", "generate_response")
workflow.add_edge("generate_response", "save_to_memory")
workflow.add_edge("save_to_memory", END)
graph = workflow.compile()

async def chat(user_id: str, message: str) -> str:
    result = await graph.ainvoke({
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "context": []
    })
    return result["messages"][-1].content
