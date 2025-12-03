import os
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

from google.adk.cli.fast_api import get_fast_api_app
from database.sqlite_db import engine, Base

# Import models to ensure they are registered with Base.metadata
from database.models import user, session, artifact, agent_config, credential, memory

# Create agent directory path
agent_directory = os.path.dirname(os.path.abspath(__file__)) + "/agents"
AGENTS_DIR = str(agent_directory)

# Lifespan context manager for database
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: Initialize DB
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Shutdown
    print("Shutting down...")
    await engine.dispose()

# Create the standard ADK FastAPI app
# We wrap it to add the database lifespan
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,
    a2a=False,
    host="0.0.0.0",
    port=8000,
    lifespan=lifespan
)

if __name__ == "__main__":
    print("========== Starting ZStyle Services (Bare Bones) ===============")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
