"""
ZStyle Services - Main Entry Point

This is the FastAPI + ADK entry point for the ZStyle system.

ARCHITECTURE:
=============
- FastAPI handles HTTP requests and ADK Dev UI
- Channels (Telegram, etc.) run as separate processes and connect via MessageRouter
- All agents are in the /agents directory and discovered by ADK

RUNNING:
========
Development:
    uvicorn main:app --reload

Production (Docker):
    docker-compose up

ADK Dev UI:
    Access at http://localhost:8000 after starting

ENVIRONMENT:
============
Required:
    - GOOGLE_API_KEY: For Gemini models

Optional:
    - PORT: Server port (default: 8000)
    - DATABASE_URL: For production PostgreSQL (defaults to SQLite)
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from google.adk.cli.fast_api import get_fast_api_app
from database.engine import engine, Base

# Import all models to ensure they're registered with Base.metadata
from database.models import User, UserMemory, ActivityLog, Credential

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create agent directory path
agent_directory = os.path.dirname(os.path.abspath(__file__)) + "/agents"
AGENTS_DIR = str(agent_directory)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI.
    
    Handles:
    - Database initialization on startup
    - Cleanup on shutdown
    """
    # Startup
    logger.info("=" * 50)
    logger.info("ZStyle Services Starting...")
    logger.info("=" * 50)
    
    # Initialize database tables
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")
    
    logger.info(f"Agents directory: {AGENTS_DIR}")
    logger.info("ADK Dev UI available at: http://localhost:8000")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("Shutting down ZStyle Services...")
    await engine.dispose()
    logger.info("Shutdown complete.")


# Create the ADK FastAPI app
# This provides:
# - ADK Dev UI at /
# - Agent API endpoints
# - Session management
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=True,      # Enable ADK Dev UI
    a2a=False,     # A2A disabled for now (enable when adding agent-to-agent)
    host="0.0.0.0",
    port=8000,
    lifespan=lifespan
)


# =============================================================================
# CUSTOM ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    """
    return {
        "status": "healthy",
        "service": "zstyle-services",
        "agents_dir": AGENTS_DIR
    }


@app.get("/api/info")
async def api_info():
    """
    API information endpoint.
    """
    return {
        "name": "ZStyle Services",
        "version": "0.1.0",
        "description": "Executive Function Coach AI System",
        "endpoints": {
            "health": "/health",
            "adk_ui": "/",
            "agent_run": "/run",
            "sessions": "/apps/{app_name}/users/{user_id}/sessions"
        }
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    logger.info("=" * 50)
    logger.info("Starting ZStyle Services (Development Mode)")
    logger.info(f"Port: {port}")
    logger.info("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
