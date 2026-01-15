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

from google.adk.cli.fast_api import get_fast_api_app
from core.database.engine import engine, Base

# Import all models to ensure they're registered with Base.metadata
from core.database.models import User, ActivityLog, Credential

# Import core configuration and logging
from core.config import settings
from core.logger import setup_logging

# Setup logging (must be called after importing settings)
setup_logging()
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
    - TelegramChannel initialization for webhook processing
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
    
    # Initialize TelegramChannel for webhook processing
    await _init_telegram_channel()
    
    logger.info(f"Agents directory: {AGENTS_DIR}")
    logger.info("ADK Dev UI available at: http://localhost:8000")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("Shutting down ZStyle Services...")
    
    # Stop TelegramChannel if initialized
    global _telegram_channel
    if _telegram_channel:
        try:
            await _telegram_channel.stop()
            logger.info("TelegramChannel stopped")
        except Exception as e:
            logger.error(f"Error stopping TelegramChannel: {e}")
    
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
    port=settings.PORT,
    lifespan=lifespan
)


# =============================================================================
# BRIDGE SETUP
# =============================================================================
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from channels.router import MessageRouter
from channels.base import NormalizedMessage, MessageType
from agents.exec_func_coach.agent import root_agent
from services.openmemory_adk_service import OpenMemoryADKService

# Initialize Bridge Components
# We create a dedicated Runner for the bridge to handle external channel requests
bridge_session_service = InMemorySessionService()
memory_service = OpenMemoryADKService()
bridge_runner = Runner(
    agent=root_agent,
    app_name="zstyle-bridge",
    session_service=bridge_session_service,
    memory_service=memory_service
)
message_router = MessageRouter(runner=bridge_runner, app_name="zstyle-bridge", session_service=bridge_session_service)

# Global TelegramChannel instance (initialized in lifespan)
_telegram_channel = None

async def _init_telegram_channel():
    """Initialize TelegramChannel and connect to message router."""
    global _telegram_channel
    try:
        from channels.telegram_bot import TelegramChannel
        from interface.telegram_webhook import set_telegram_channel
        
        logger.info("Initializing TelegramChannel for webhook processing...")
        _telegram_channel = TelegramChannel()
        
        # Set message handler to route messages through message_router
        _telegram_channel.set_message_handler(message_router.route)
        
        # Initialize Application for bot operations (without polling)
        await _telegram_channel.start()
        
        # Set telegram channel for webhook router
        set_telegram_channel(_telegram_channel)
        logger.info("TelegramChannel initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize TelegramChannel: {e}")
        logger.warning("Webhook endpoint will not be available")
        _telegram_channel = None

class BridgeRequest(BaseModel):
    """
    JSON-safe representation of NormalizedMessage for API transport.
    """
    channel: str
    user_id: str
    channel_user_id: str
    session_id: str
    content_type: str
    text: Optional[str] = None
    attachments: List[str] = []  # Base64 strings
    metadata: Dict[str, Any] = {}


@app.post("/api/chat")
async def chat_bridge(request: BridgeRequest):
    """
    Bridge endpoint for external channels (Telegram, etc.) to access the agent.
    """
    logger.info(f"Bridge received message from {request.channel} user {request.user_id}")
    
    try:
        import base64
        
        # Decode attachments if present
        decoded_attachments = []
        if request.attachments:
            for attach_str in request.attachments:
                try:
                    decoded_attachments.append(base64.b64decode(attach_str))
                except Exception as e:
                    logger.error(f"Failed to decode attachment: {e}")
        
        # Convert to NormalizedMessage
        msg = NormalizedMessage(
            channel=request.channel,
            user_id=request.user_id,
            channel_user_id=request.channel_user_id,
            session_id=request.session_id,
            content_type=MessageType(request.content_type),
            text=request.text,
            attachments=decoded_attachments,
            metadata=request.metadata
        )
        
        # Route to agent
        response_text = await message_router.route(msg)
        
        return {"response": response_text}
        
    except Exception as e:
        logger.error(f"Bridge error: {e}", exc_info=True)
        return {"response": "I encountered an internal error. Please try again."}


# =============================================================================
# OAUTH ROUTERS
# =============================================================================

from interface.oauth.google import router as google_oauth_router
from interface.oauth.ticktick import router as ticktick_oauth_router

app.include_router(google_oauth_router)
app.include_router(ticktick_oauth_router)


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
            "sessions": "/apps/{app_name}/users/{user_id}/sessions",
            "telegram_webhook": "/webhook/telegram"
        }
    }


# =============================================================================
# WEBHOOK ROUTER
# =============================================================================
from interface.telegram_webhook import router as webhook_router

app.include_router(webhook_router)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting ZStyle Services (Development Mode)")
    logger.info(f"Port: {settings.PORT}")
    logger.info("=" * 50)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )
