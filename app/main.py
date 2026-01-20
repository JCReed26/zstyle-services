"""
ZStyle Services - Main Entry Point

This is the FastAPI + ADK entry point for the ZStyle system.

ARCHITECTURE:
=============
- FastAPI handles HTTP requests and ADK Dev UI
- Channels (Telegram, etc.) run as separate processes and connect via MessageRouter
- All agents are in the /agent directory and discovered by ADK

RUNNING:
========
Development:
    uvicorn app.main:app --reload

Production (Docker):
    docker-compose up

ADK Dev UI:
    Access at http://localhost:8000 after starting

ENVIRONMENT:
============
Required:
    - GOOGLE_API_KEY: For Gemini models
    - DATABASE_URL: PostgreSQL connection string (Supabase)
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from google.adk.cli.fast_api import get_fast_api_app
from database.engine import engine, Base

# Import all models to ensure they're registered with Base.metadata
from database.models import User, ActivityLog, Credential, OAuthState

# Import core configuration and logging
from app.config import settings
from app.logger import setup_logging

# Setup logging (must be called after importing settings)
setup_logging()
logger = logging.getLogger(__name__)

# Create agent directory path
agent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/agent"
AGENTS_DIR = str(agent_directory)


def validate_critical_imports():
    """
    Validate all critical imports at startup.
    Raises ImportError if any critical import fails.
    """
    critical_imports = [
        ("openmemory.client", "Memory", "openmemory-py package"),
        ("google.adk.agents", "Agent", "google-adk package"),
        ("google.adk.tools.agent_tool", "AgentTool", "google-adk package"),
    ]
    
    failed_imports = []
    for module_name, class_name, description in critical_imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            if not hasattr(module, class_name):
                failed_imports.append(f"{module_name}.{class_name} ({description})")
        except (ImportError, NameError, AttributeError) as e:
            failed_imports.append(f"{module_name}.{class_name} ({description}): {e}")
    
    if failed_imports:
        error_msg = "Critical imports failed:\n" + "\n".join(f"  - {imp}" for imp in failed_imports)
        logger.error(error_msg)
        raise ImportError(error_msg)
    
    logger.info("All critical imports validated successfully")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI.
    
    Handles:
    - Critical import validation
    - Database initialization on startup
    - TelegramChannel initialization for webhook processing
    - Cleanup on shutdown
    """
    # Startup
    logger.info("=" * 50)
    logger.info("ZStyle Services Starting...")
    logger.info("=" * 50)
    
    # Validate critical imports at startup
    validate_critical_imports()
    
    # Register database engine with availability checker
    from database.availability import set_database_engine, is_database_available
    set_database_engine(engine)
    
    # Initialize database tables (non-blocking)
    if is_database_available() and engine:
        logger.info("Initializing database...")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            logger.warning("Application continuing without database - some features may be limited")
            set_database_engine(None)  # Mark database as unavailable
            # Don't raise - allow app to start even if DB is unavailable
            # This is important for development and graceful degradation
    else:
        logger.warning("Database not configured - application running in degraded mode")
        logger.warning("User management features will be disabled")
    
    # Initialize TelegramChannel for webhook processing
    await _init_telegram_channel()
    
    # Start background task for OAuth state cleanup (only if database available)
    if is_database_available():
        import asyncio
        from services.oauth_state_service import oauth_state_service
        
        async def cleanup_oauth_states():
            """Periodically clean up expired OAuth states."""
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    if is_database_available():
                        deleted = await oauth_state_service.cleanup_expired()
                        if deleted > 0:
                            logger.info(f"Cleaned up {deleted} expired OAuth states")
                except Exception as e:
                    logger.error(f"Error cleaning up OAuth states: {e}")
        
        # Start cleanup task
        asyncio.create_task(cleanup_oauth_states())
    
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
    
    if engine:
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
from agent.exec_func_coach.agent import root_agent
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
        
        logger.info("Initializing TelegramChannel for webhook processing...")
        _telegram_channel = TelegramChannel()
        
        # Set message handler to route messages through message_router
        _telegram_channel.set_message_handler(message_router.route)
        
        # Initialize Application for bot operations (without polling)
        await _telegram_channel.start()
        
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
# OAUTH ROUTES (Simple inline implementation)
# =============================================================================

from fastapi import Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import urlencode
import httpx
from uuid import UUID

from services.oauth_state_service import oauth_state_service
from services.credential_service import credential_service
from database.availability import is_database_available

@app.get("/oauth/webapp")
async def oauth_webapp(service: str = Query(...), user_id: str = Query(...)):
    """Simple webapp redirect for Telegram Mini App."""
    try:
        UUID(user_id)  # Validate UUID
    except ValueError:
        raise HTTPException(400, "Invalid user_id")
    
    if service == "google" and settings.GOOGLE_CLIENT_ID:
        base_url = settings.OAUTH_BASE_URL or f"http://localhost:{settings.PORT}"
        auth_url = f"{base_url}/oauth/google/authorize?user_id={user_id}"
    elif service == "ticktick" and settings.TICKTICK_CLIENT_ID:
        base_url = settings.OAUTH_BASE_URL or f"http://localhost:{settings.PORT}"
        auth_url = f"{base_url}/oauth/ticktick/authorize?user_id={user_id}"
    else:
        raise HTTPException(400, "Service not configured")
    
    return HTMLResponse(f'<html><body><script>window.location.href="{auth_url}";</script></body></html>')

@app.get("/oauth/google/authorize")
async def google_authorize(user_id: str = Query(...)):
    """Start Google OAuth flow."""
    try:
        UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")
    
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    
    if not is_database_available():
        raise HTTPException(503, "Database unavailable")
    
    state = await oauth_state_service.create_state(user_id, "google")
    base_url = settings.OAUTH_BASE_URL or f"http://localhost:{settings.PORT}"
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{base_url}/oauth/google/callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/gmail.readonly",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

@app.get("/oauth/google/callback")
async def google_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """Handle Google OAuth callback."""
    if error:
        return HTMLResponse(f"<html><body><h1>Error: {error}</h1></body></html>", 400)
    
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    
    if not is_database_available():
        raise HTTPException(503, "Database unavailable")
    
    state_data = await oauth_state_service.validate_and_consume(state)
    if not state_data:
        return HTMLResponse("<html><body><h1>Invalid or expired request</h1></body></html>", 400)
    
    user_id = str(state_data["user_id"])
    base_url = settings.OAUTH_BASE_URL or f"http://localhost:{settings.PORT}"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{base_url}/oauth/google/callback",
                "grant_type": "authorization_code"
            })
            resp.raise_for_status()
            tokens = resp.json()
        
        await credential_service.store_credentials(user_id, "google", {
            "token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600)
        })
        
        return HTMLResponse("<html><body><h1>Success! You can close this window.</h1></body></html>")
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return HTMLResponse(f"<html><body><h1>Error: {str(e)}</h1></body></html>", 500)


# =============================================================================
# CUSTOM ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    Verifies service dependencies are available.
    """
    from database.availability import is_database_available
    from services.openmemory_client import get_openmemory_client
    
    status = {"status": "healthy", "service": "zstyle-services"}
    checks = {}
    
    # Database check
    checks["database"] = "available" if is_database_available() else "unavailable"
    
    # OpenMemory check
    try:
        client = get_openmemory_client()
        # Simple connectivity check
        checks["openmemory"] = "available"
    except Exception:
        checks["openmemory"] = "unavailable"
    
    # Determine overall health
    if all(v == "available" for v in checks.values()):
        status["status"] = "healthy"
    else:
        status["status"] = "degraded"
    
    status["checks"] = checks
    return status


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
            "telegram_polling": "Telegram bot uses polling mode"
        }
    }


# =============================================================================
# WEBHOOK ROUTER
# =============================================================================
from fastapi import Request, HTTPException
from telegram import Update
from app.security import verify_telegram_webhook

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    
    Receives updates from Telegram and processes them through TelegramChannel.
    """
    if not _telegram_channel:
        raise HTTPException(status_code=503, detail="Telegram channel not initialized")
    
    # Verify webhook secret if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        body = await request.body()
        if not verify_telegram_webhook(body, settings.TELEGRAM_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Parse update from JSON
    try:
        data = await request.json()
        update = Update.de_json(data, _telegram_channel.application.bot)
        
        # Process update
        await _telegram_channel.process_webhook_update(update)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing webhook")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Starting ZStyle Services (Development Mode)")
    logger.info(f"Port: {settings.PORT}")
    logger.info("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )
