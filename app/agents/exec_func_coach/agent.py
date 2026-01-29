from datetime import datetime
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.agents.personal_assistant.agent import agent as personal_assistant_agent

import os

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

@tool
def get_datetime(date: str) -> str:
    """Get the datetime of a given date"""
    return datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")

@tool
async def delegate_to_personal_assistant(state):
    """Delegate to the personal assistant"""
    return personal_assistant_agent.invoke(state)

tools = [get_datetime, delegate_to_personal_assistant]

system_prompt = "You are a helpful assistant that can search the web."

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)
