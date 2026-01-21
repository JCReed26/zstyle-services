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
    - DATABASE_URL: PostgreSQL connection string (local container)
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException

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


def get_validated_oauth_base_url() -> str:
    """
    Get and validate OAUTH_BASE_URL from settings.
    
    Raises:
        HTTPException: If OAUTH_BASE_URL is not set or not HTTPS
    """
    base_url = settings.OAUTH_BASE_URL
    if not base_url:
        raise HTTPException(503, "OAUTH_BASE_URL not configured. Set it in .env file.")
    if not base_url.startswith("https://"):
        raise HTTPException(503, "OAUTH_BASE_URL must be HTTPS. Use ngrok for development.")
    return base_url.rstrip('/')


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
    
    # Verify database connection (schema should already exist via migration)
    if is_database_available() and engine:
        logger.info("Verifying database connection...")
        try:
            from sqlalchemy import text
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified successfully.")
        except Exception as e:
            logger.error(f"Database connection failed: {e}", exc_info=True)
            logger.warning("Application continuing without database - some features may be limited")
            set_database_engine(None)  # Mark database as unavailable
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

from fastapi import Query, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import urlencode
import httpx
from uuid import UUID

from services.oauth_state_service import oauth_state_service
from services.credential_service import credential_service
from database.availability import is_database_available

@app.get("/oauth/webapp")
async def oauth_webapp(service: str = Query(...), user_id: str = Query(...)):
    """
    Webapp endpoint for Telegram Mini App OAuth flow.
    
    This endpoint serves an HTML page that:
    1. Opens OAuth provider URL in external browser (not iframe)
    2. Handles the callback and closes the webapp
    """
    try:
        UUID(user_id)  # Validate UUID
    except ValueError:
        raise HTTPException(400, "Invalid user_id")
    
    if service == "google" and settings.GOOGLE_CLIENT_ID:
        base_url = get_validated_oauth_base_url()
        auth_url = f"{base_url}/oauth/google/authorize?user_id={user_id}"
    elif service == "ticktick" and settings.TICKTICK_CLIENT_ID:
        base_url = get_validated_oauth_base_url()
        auth_url = f"{base_url}/oauth/ticktick/authorize?user_id={user_id}"
    else:
        raise HTTPException(400, "Service not configured")
    
    # Return HTML page that opens OAuth in external browser
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authorizing {service.title()}...</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
            }}
            .container {{
                text-align: center;
                padding: 20px;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #0088cc;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            button {{
                padding: 12px 24px;
                background: var(--tg-theme-button-color, #0088cc);
                color: var(--tg-theme-button-text-color, #ffffff);
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner"></div>
            <p>Opening {service.title()} authorization...</p>
            <p style="font-size: 14px; color: #666; margin-top: 10px;">
                If the authorization page doesn't open automatically, click the button below.
            </p>
            <button onclick="openAuth()">Open Authorization Page</button>
        </div>
        <script>
            // Expand webapp to full height
            if (window.Telegram && window.Telegram.WebApp) {{
                window.Telegram.WebApp.expand();
            }}
            
            function openAuth() {{
                const authUrl = "{auth_url}";
                if (window.Telegram && window.Telegram.WebApp) {{
                    // Use Telegram's openLink to open in external browser
                    window.Telegram.WebApp.openLink(authUrl);
                }} else {{
                    // Fallback for non-Telegram environments
                    window.open(authUrl, '_blank');
                }}
            }}
            
            // Auto-open after a short delay
            setTimeout(openAuth, 500);
        </script>
    </body>
    </html>
    """
    response = HTMLResponse(html_content)
    # Add CSP header for Telegram WebApp embedding
    response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
    return response

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
    base_url = get_validated_oauth_base_url()
    redirect_uri = f"{base_url}/oauth/google/callback"
    logger.info(f"DEBUG Google redirect_uri: '{redirect_uri}'")  # Add this line
    logger.info(f"DEBUG Google base_url: '{base_url}'")  # Add this line
    logger.info(f"DEBUG Google state: '{state}'")  # Add this line
    logger.info(f"DEBUG Google settings.GOOGLE_CLIENT_ID: '{settings.GOOGLE_CLIENT_ID}'")  # Add this line
    logger.info(f"DEBUG Google settings.GOOGLE_CLIENT_SECRET: '{settings.GOOGLE_CLIENT_SECRET}'")  # Add this line

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
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Error</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Authorization Failed</h1>
            <p>Error: {}</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """.format(error)
        response = HTMLResponse(html, 400)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    
    if not is_database_available():
        raise HTTPException(503, "Database unavailable")
    
    state_data = await oauth_state_service.validate_and_consume(state)
    if not state_data:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invalid Request</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Invalid or Expired Request</h1>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html, 400)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    
    user_id = str(state_data["user_id"])
    base_url = get_validated_oauth_base_url()
    
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
        
        # Store credentials with expires_at calculation (handled by credential_service)
        await credential_service.store_credentials(user_id, "google", {
            "token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600)
        })
        
        # Success page that closes the webapp
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Successful</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: var(--tg-theme-bg-color, #ffffff);
                    color: var(--tg-theme-text-color, #000000);
                    text-align: center;
                    padding: 20px;
                }}
                .success {{
                    color: #4caf50;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div>
                <div class="success">✓</div>
                <h1>Authorization Successful!</h1>
                <p>You can close this window.</p>
            </div>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    // Close the webapp after 2 seconds
                    setTimeout(() => {{
                        window.Telegram.WebApp.close();
                    }}, 2000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Error</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Error</h1>
            <p>{str(e)}</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html, 500)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response


# =============================================================================
# TICKTICK OAUTH ROUTES
# =============================================================================

@app.get("/oauth/ticktick/authorize")
async def ticktick_authorize(user_id: str = Query(...)):
    """Start TickTick OAuth flow."""
    try:
        UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")
    
    if not settings.TICKTICK_CLIENT_ID:
        raise HTTPException(503, "TickTick OAuth not configured")
    
    if not is_database_available():
        raise HTTPException(503, "Database unavailable")
    
    state = await oauth_state_service.create_state(user_id, "ticktick")
    base_url = get_validated_oauth_base_url()
    redirect_uri = f"{base_url}/oauth/ticktick/callback"
    
    # TickTick OAuth 2.0 authorization URL
    # Documentation: https://developer.ticktick.com/api#oauth
    params = {
        "client_id": settings.TICKTICK_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "tasks:write tasks:read",
        "state": state,
    }
    
    auth_url = f"https://ticktick.com/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@app.get("/oauth/ticktick/callback")
async def ticktick_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """Handle TickTick OAuth callback."""
    if error:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Error</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Authorization Failed</h1>
            <p>Error: {}</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """.format(error)
        response = HTMLResponse(html, 400)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    
    if not is_database_available():
        raise HTTPException(503, "Database unavailable")
    
    state_data = await oauth_state_service.validate_and_consume(state)
    if not state_data:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Invalid Request</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Invalid or Expired Request</h1>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html, 400)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    
    user_id = str(state_data["user_id"])
    
    try:
        base_url = get_validated_oauth_base_url()
        redirect_uri = f"{base_url}/oauth/ticktick/callback"
        
        # Exchange authorization code for access token
        token_url = "https://ticktick.com/oauth/token"
        token_data = {
            "client_id": settings.TICKTICK_CLIENT_ID,
            "client_secret": settings.TICKTICK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()
        
        # Store credentials
        await credential_service.store_credentials(user_id, "ticktick", {
            "token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": tokens.get("expires_in", 3600),
        })
        
        # Send confirmation message to user via Telegram
        try:
            from database.repositories import UserRepository
            from database.engine import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_id(user_id)
                
                if user and user.telegram_id and _telegram_channel:
                    confirmation_message = (
                        "✅ TickTick authorization successful!\n\n"
                        "Your TickTick account has been connected. "
                        "You can now use TickTick features like:\n"
                        "• View your tasks\n"
                        "• Create new tasks\n"
                        "• Update task status\n"
                        "• Manage your projects"
                    )
                    
                    await _telegram_channel.send_response(
                        user_id=user_id,
                        response=confirmation_message,
                        channel_user_id=str(user.telegram_id)
                    )
                    logger.info(f"Sent TickTick authorization confirmation to user {user_id} (Telegram: {user.telegram_id})")
                elif not user:
                    logger.warning(f"User {user_id} not found - cannot send confirmation message")
                elif not user.telegram_id:
                    logger.warning(f"User {user_id} has no Telegram ID - cannot send confirmation message")
                elif not _telegram_channel:
                    logger.warning("Telegram channel not initialized - cannot send confirmation message")
        except Exception as e:
            # Don't fail the OAuth flow if sending message fails
            logger.error(f"Failed to send TickTick authorization confirmation message: {e}", exc_info=True)
        
        # Success page that closes the webapp
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Successful</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: var(--tg-theme-bg-color, #ffffff);
                    color: var(--tg-theme-text-color, #000000);
                    text-align: center;
                    padding: 20px;
                }}
                .success {{
                    color: #4caf50;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div>
                <div class="success">✓</div>
                <h1>Authorization Successful!</h1>
                <p>You can close this window.</p>
            </div>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    // Close the webapp after 2 seconds
                    setTimeout(() => {{
                        window.Telegram.WebApp.close();
                    }}, 2000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
        
    except httpx.HTTPStatusError as e:
        logger.error(f"TickTick token exchange failed: {e.response.status_code} - {e.response.text}", exc_info=True)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Error</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Authorization Failed</h1>
            <p>Error: {e.response.status_code}</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html, 500)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response
    except Exception as e:
        logger.error(f"TickTick OAuth callback error: {e}", exc_info=True)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Authorization Error</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <meta http-equiv="Content-Security-Policy" content="frame-ancestors https://web.telegram.org https://*.web.telegram.org;">
        </head>
        <body style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Authorization Failed</h1>
            <p>An error occurred: {str(e)}</p>
            <script>
                if (window.Telegram && window.Telegram.WebApp) {{
                    setTimeout(() => window.Telegram.WebApp.close(), 3000);
                }}
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(html, 500)
        response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
        return response


# =============================================================================
# PHONE AUTH WEB APP
# =============================================================================

@app.get("/auth/phone")
async def phone_auth_webapp(telegram_id: str = Query(...)):
    """
    Web app for phone number authentication (simplified - no OTP).
    Note: Primary authentication flow is via Telegram contact sharing.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phone Authentication</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
            }}
            .container {{
                max-width: 400px;
                margin: 0 auto;
            }}
            input {{
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                box-sizing: border-box;
            }}
            button {{
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                background: var(--tg-theme-button-color, #0088cc);
                color: var(--tg-theme-button-text-color, #ffffff);
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
            }}
            .error {{
                color: #ff3333;
                margin: 10px 0;
            }}
            .success {{
                color: #4caf50;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Phone Authentication</h1>
            <div id="phoneStep">
                <p>Enter your phone number (E.164 format, e.g., +1234567890):</p>
                <input type="tel" id="phoneNumber" placeholder="+1234567890" />
                <button onclick="createUser()">Create Account</button>
                <div id="phoneError" class="error"></div>
            </div>
            <div id="successStep" style="display: none;">
                <div class="success">✓ Authentication successful!</div>
                <p>You can close this window.</p>
            </div>
        </div>
        <script>
            if (window.Telegram && window.Telegram.WebApp) {{
                window.Telegram.WebApp.expand();
            }}
            
            const telegramId = '{telegram_id}';
            
            async function createUser() {{
                const phoneNumber = document.getElementById('phoneNumber').value.trim();
                if (!phoneNumber) {{
                    document.getElementById('phoneError').textContent = 'Please enter your phone number';
                    return;
                }}
                
                const formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : '+' + phoneNumber;
                
                try {{
                    const response = await fetch('/api/auth/phone/create', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            phone_number: formattedPhone,
                            telegram_id: telegramId
                        }})
                    }});
                    
                    const data = await response.json();
                    if (data.success) {{
                        document.getElementById('phoneStep').style.display = 'none';
                        document.getElementById('successStep').style.display = 'block';
                        if (window.Telegram && window.Telegram.WebApp) {{
                            setTimeout(() => window.Telegram.WebApp.close(), 2000);
                        }}
                    }} else {{
                        document.getElementById('phoneError').textContent = data.error || 'Failed to create account';
                    }}
                }} catch (e) {{
                    document.getElementById('phoneError').textContent = 'Error: ' + e.message;
                }}
            }}
        </script>
    </body>
    </html>
    """
    response = HTMLResponse(html_content)
    response.headers["Content-Security-Policy"] = "frame-ancestors https://web.telegram.org https://*.web.telegram.org;"
    return response

@app.post("/api/auth/phone/create")
async def create_user_api(request: Request):
    """API endpoint to create user with phone number and Telegram ID."""
    from services.auth_service import auth_service
    data = await request.json()
    phone_number = data.get('phone_number')
    telegram_id = data.get('telegram_id')
    telegram_username = data.get('telegram_username')
    
    try:
        if not telegram_id:
            return {"success": False, "error": "telegram_id is required"}
        
        result = await auth_service.create_user_with_phone(
            phone_number=phone_number,
            telegram_id=int(telegram_id),
            telegram_username=telegram_username
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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
