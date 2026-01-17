"""
TickTick OAuth2 endpoints.

Handles OAuth2 flow for TickTick task management service.
"""
import time
import asyncio
from typing import Dict, Any

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from ticktick.oauth2 import OAuth2

from services import credential_service
from services.oauth_state_service import oauth_state_service
from api.oauth.utils import get_redirect_uri
from app.config import settings

router = APIRouter()


@router.get("/oauth/ticktick/initiate")
async def initiate_ticktick_oauth(user_id: str = Query(..., description="User ID for OAuth flow")):
    """
    Initiate TickTick OAuth2 flow.
    
    Generates a secure state token and returns the authorization URL.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with authorization URL and state token
    """
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="TickTick OAuth not configured. TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET are required."
        )
    
    # Generate and store state token in database
    state = await oauth_state_service.create_state(
        user_id=user_id,
        service="ticktick"
    )
    
    # Create OAuth2 client
    redirect_uri = get_redirect_uri("ticktick")
    oauth_client = OAuth2(
        client_id=settings.TICKTICK_CLIENT_ID,
        client_secret=settings.TICKTICK_CLIENT_SECRET,
        redirect_uri=redirect_uri
    )
    
    # Get authorization URL
    # Note: ticktick-py's get_authorization_url may need state parameter
    # If it doesn't support state, we'll need to append it manually
    try:
        auth_url = await asyncio.to_thread(oauth_client.get_authorization_url, state=state)
    except TypeError:
        # If get_authorization_url doesn't accept state, get base URL and append state
        auth_url = await asyncio.to_thread(oauth_client.get_authorization_url)
        if "state=" not in auth_url:
            separator = "&" if "?" in auth_url else "?"
            auth_url = f"{auth_url}{separator}state={state}"
    
    return {"url": auth_url, "state": state}


@router.get("/oauth/ticktick/callback")
async def ticktick_oauth_callback(
    code: str = Query(None, description="Authorization code from TickTick"),
    state: str = Query(..., description="State token from initiation"),
    error: str = Query(None, description="Error from OAuth provider"),
    error_description: str = Query(None, description="Error description")
):
    """
    Handle TickTick OAuth2 callback.
    
    Validates state, exchanges authorization code for tokens, and stores credentials.
    Returns HTML page for Telegram WebView.
    
    Args:
        code: Authorization code from TickTick
        state: State token from initiation
        error: Error code if authorization failed
        error_description: Error description if authorization failed
        
    Returns:
        HTMLResponse with success or error page
    """
    # Handle OAuth provider errors
    if error:
        return _render_error_html("ticktick", error, error_description)
    
    if not code:
        return _render_error_html("ticktick", "missing_code", "Authorization code not provided")
    
    # Validate and consume state token
    state_data = await oauth_state_service.validate_and_consume(state)
    
    if not state_data:
        return _render_error_html("ticktick", "invalid_state", "Invalid or expired state token")
    
    user_id = state_data["user_id"]
    
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        return _render_error_html("ticktick", "config_error", "TickTick OAuth not configured")
    
    try:
        # Create OAuth2 client
        redirect_uri = get_redirect_uri("ticktick")
        oauth_client = OAuth2(
            client_id=settings.TICKTICK_CLIENT_ID,
            client_secret=settings.TICKTICK_CLIENT_SECRET,
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for tokens
        token_response = await asyncio.to_thread(
            oauth_client.get_access_token,
            code
        )
        
        # Extract token information
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        
        # Calculate expiration timestamp
        expires_at = int(time.time()) + expires_in
        
        # Prepare credentials for storage
        credentials_dict: Dict[str, Any] = {
            "token": access_token,
            "expires_at": expires_at,
            "expires_in": expires_in
        }
        
        if refresh_token:
            credentials_dict["refresh_token"] = refresh_token
        
        # Store credentials
        await credential_service.store_credentials(
            user_id=user_id,
            service="ticktick",
            credentials=credentials_dict
        )
        
        return _render_success_html("ticktick")
        
    except Exception as e:
        # Log error details server-side
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"TickTick OAuth token exchange failed: {e}", exc_info=True)
        
        return _render_error_html("ticktick", "token_exchange_failed", str(e))


def _render_success_html(service: str) -> HTMLResponse:
    """Render success HTML page."""
    service_name = {"google": "Google", "ticktick": "TickTick"}.get(service, "Service")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authorization Successful</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
                padding: 20px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
            }}
            .success-icon {{
                font-size: 64px;
                margin-bottom: 20px;
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 10px;
                color: var(--tg-theme-text-color, #000000);
            }}
            p {{
                font-size: 16px;
                color: var(--tg-theme-hint-color, #999999);
                margin-bottom: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="success-icon">✅</div>
        <h1>Authorization Successful!</h1>
        <p>You have successfully authorized {service_name}.</p>
        <p>You can close this window.</p>
        <script>
            if (window.Telegram && window.Telegram.WebApp) {{
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                setTimeout(() => {{
                    window.Telegram.WebApp.close();
                }}, 2000);
            }} else {{
                setTimeout(() => window.close(), 2000);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def _render_error_html(service: str, error: str, description: str = None) -> HTMLResponse:
    """Render error HTML page."""
    service_name = {"google": "Google", "ticktick": "TickTick"}.get(service, "Service")
    error_message = description or error
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authorization Failed</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
                padding: 20px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
            }}
            .error-icon {{
                font-size: 64px;
                margin-bottom: 20px;
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 10px;
                color: var(--tg-theme-destructive-text-color, #ff0000);
            }}
            p {{
                font-size: 16px;
                color: var(--tg-theme-hint-color, #999999);
                margin-bottom: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="error-icon">❌</div>
        <h1>Authorization Failed</h1>
        <p>{error_message}</p>
        <p>Please try again or contact support if the problem persists.</p>
        <script>
            if (window.Telegram && window.Telegram.WebApp) {{
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
