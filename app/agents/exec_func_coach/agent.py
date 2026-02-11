from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.exec_func_coach.prompts import SYSTEM_PROMPT

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.7)


async def chat(user_id: str, message: str) -> str:
    """Chat with executive function coach agent."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message)
    ]
    response = llm.invoke(messages)
    return response.content
