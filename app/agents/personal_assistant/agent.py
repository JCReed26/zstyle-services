from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.agents.personal_assistant.prompts import SYSTEM_PROMPT

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)


async def chat(user_id: str, message: str) -> str:
    """Chat with personal assistant agent."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message)
    ]
    response = llm.invoke(messages)
    return response.content
