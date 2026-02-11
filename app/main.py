from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ZStyle Services")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    agent: str


AGENTS = {
    "exec_func_coach": "app.agents.exec_func_coach",
    "fitness_coach": "app.agents.fitness_coach",
    "nutritionist": "app.agents.nutritionist",
    "personal_assistant": "app.agents.personal_assistant",
}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/v1/chat/{agent_name}")
async def chat(agent_name: str, request: ChatRequest):
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    # Lazy import to avoid loading all agents at startup
    import importlib
    module = importlib.import_module(AGENTS[agent_name])
    response = await module.chat(request.user_id, request.message)
    return ChatResponse(response=response, agent=agent_name)
