from langchain_core import tools
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
import os

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
tools_list = []

system_prompt = "You are a helpful assistant that can help with nutrition."

agent = create_agent(
    model=llm,
    tools=tools_list,
    system_prompt=system_prompt
)
