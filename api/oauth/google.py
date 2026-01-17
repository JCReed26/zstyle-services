"""
Google OAuth2 endpoints.

Handles OAuth2 flow for Google services (Calendar, Gmail, etc.).
"""
from typing import Dict, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from services import credential_service
from services.oauth_state_service import oauth_state_service
from api.oauth.utils import get_redirect_uri
from app.config import settings

router = APIRouter()


def _build_authorization_url(state: str) -> str:
    """
    Build Google OAuth2 authorization URL.
    
    Args:
        state: OAuth state token for CSRF protection
        
    Returns:
        Authorization URL
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. GOOGLE_CLIENT_ID is required."
        )
    
    redirect_uri = get_redirect_uri("google")  # Use helper function
    scope = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.readonly"
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "code",
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Always show consent screen to get refresh token
        "state": state
    }
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


@router.get("/oauth/google/initiate")
async def initiate_google_oauth(user_id: str = Query(..., description="User ID for OAuth flow")):
    """
    Initiate Google OAuth2 flow.
    
    Generates a secure state token and returns the authorization URL.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dictionary with authorization URL and state token
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required."
        )
    
    # Generate and store state token in database
    state = await oauth_state_service.create_state(
        user_id=user_id,
        service="google"
    )
    
    # Build authorization URL
    url = _build_authorization_url(state)
    
    return {"url": url, "state": state}


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str = Query(None, description="Authorization code from Google"),
    state: str = Query(..., description="State token from initiation"),
    error: str = Query(None, description="Error from OAuth provider"),
    error_description: str = Query(None, description="Error description")
):
    """
    Handle Google OAuth2 callback.
    
    Validates state, exchanges authorization code for tokens, and stores credentials.
    Returns HTML page for Telegram WebView.
    
    Args:
        code: Authorization code from Google
        state: State token from initiation
        error: Error code if authorization failed
        error_description: Error description if authorization failed
        
    Returns:
        HTMLResponse with success or error page
    """
    # Handle OAuth provider errors
    if error:
        return _render_error_html("google", error, error_description)
    
    if not code:
        return _render_error_html("google", "missing_code", "Authorization code not provided")
    
    # Validate and consume state token
    state_data = await oauth_state_service.validate_and_consume(state)
    
    if not state_data:
        return _render_error_html("google", "invalid_state", "Invalid or expired state token")
    
    user_id = state_data["user_id"]
    
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return _render_error_html("google", "config_error", "Google OAuth not configured")
    
    try:
        # Create OAuth2 flow
        redirect_uri = get_redirect_uri("google")
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.readonly"],
            redirect_uri=redirect_uri
        )
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        
        # Get credentials
        credentials: Credentials = flow.credentials
        
        # Prepare credentials for storage
        credentials_dict: Dict[str, Any] = {
            "token": credentials.token,
            "token_type": "Bearer"
        }
        
        if credentials.refresh_token:
            credentials_dict["refresh_token"] = credentials.refresh_token
        
        if credentials.expiry:
            # Convert datetime to timestamp
            credentials_dict["expires_at"] = credentials.expiry.timestamp()
        
        if credentials.scopes:
            credentials_dict["scope"] = " ".join(credentials.scopes)
        
        # Store credentials
        await credential_service.store_credentials(
            user_id=user_id,
            service="google",
            credentials=credentials_dict
        )
        
        return _render_success_html("google")
        
    except Exception as e:
        # Log error details server-side
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Google OAuth token exchange failed: {e}", exc_info=True)
        
        return _render_error_html("google", "token_exchange_failed", str(e))


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
