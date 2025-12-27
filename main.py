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
from database.core import engine, Base

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
# BRIDGE SETUP
# =============================================================================
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from channels.router import MessageRouter
from channels.base import NormalizedMessage, MessageType
from agents.exec_func_coach.agent import root_agent

# Initialize Bridge Components
# We create a dedicated Runner for the bridge to handle external channel requests
bridge_session_service = InMemorySessionService()
bridge_runner = Runner(agent=root_agent, app_name="zstyle-bridge", session_service=bridge_session_service)
message_router = MessageRouter(runner=bridge_runner, app_name="zstyle-bridge", session_service=bridge_session_service)

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
# OAUTH CALLBACK ENDPOINTS
# =============================================================================

@app.get("/api/oauth/ticktick/callback")
async def ticktick_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth callback endpoint for TickTick authorization.
    
    Handles the redirect from TickTick OAuth flow.
    """
    from fastapi.responses import HTMLResponse
    from agents.exec_func_coach.helpers import submit_ticktick_auth_code
    
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please try again.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code or not state:
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Invalid Request</h1>
                    <p>Missing code or state parameter.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    try:
        # Submit the auth code (state validation happens inside)
        result = await submit_ticktick_auth_code(
            code=code,
            tool_context=None,
            user_id=None,
            state=state
        )
        
        if result.get("status") == "success":
            return HTMLResponse(
                content="""
                <html>
                    <body>
                        <h1>Authorization Successful!</h1>
                        <p>TickTick has been successfully connected to your account.</p>
                        <p>You can close this window and return to the app.</p>
                    </body>
                </html>
                """
            )
        else:
            return HTMLResponse(
                content=f"""
                <html>
                    <body>
                        <h1>Authorization Failed</h1>
                        <p>{result.get('message', 'Unknown error occurred')}</p>
                    </body>
                </html>
                """,
                status_code=400
            )
    except Exception as e:
        logger.error(f"TickTick OAuth callback error: {e}", exc_info=True)
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Internal Error</h1>
                    <p>An error occurred while processing your authorization.</p>
                    <p>Please try again later.</p>
                </body>
            </html>
            """,
            status_code=500
        )


@app.get("/api/oauth/google/callback")
async def google_oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth callback endpoint for Google (Gmail/Calendar) authorization.
    
    Handles the redirect from Google OAuth flow.
    """
    from fastapi.responses import HTMLResponse
    from agents.exec_func_coach.helpers import submit_google_auth_code
    
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please try again.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code or not state:
        return HTMLResponse(
            content="""
            <html>
                <body>
                    <h1>Invalid Request</h1>
                    <p>Missing code or state parameter.</p>
                </body>
            </html>
            """,
            status_code=400
        )
    
    try:
        # Submit the auth code (state validation happens inside)
        result = await submit_google_auth_code(
            code=code,
            tool_context=None,
            user_id=None,
            state=state
        )
        
        if result.get("status") == "success":
            return HTMLResponse(
                content="""
                <html>
                    <body>
                        <h1>Authorization Successful!</h1>
                        <p>Google (Gmail and Calendar) has been successfully connected to your account.</p>
                        <p>You can close this window and return to the app.</p>
                    </body>
                </html>
                """
            )
        else:
            return HTMLResponse(
                content=f"""
                <html>
                    <body>
                        <h1>Authorization Failed</h1>
                        <p>{result.get('message', 'Unknown error occurred')}</p>
                    </body>
                </html>
                """,
                status_code=400
            )
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}", exc_info=True)
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>Internal Error</h1>
                    <p>An error occurred while processing your authorization.</p>
                    <p>Please try again later.</p>
                </body>
            </html>
            """,
            status_code=500
        )


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
