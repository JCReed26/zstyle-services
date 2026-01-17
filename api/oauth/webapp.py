"""
OAuth Web App Route

Serves the HTML page for Telegram Web App OAuth flow.
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()


@router.get("/oauth/webapp")
async def oauth_webapp(
    service: str = Query(..., description="OAuth service name (google, ticktick)"),
    user_id: str = Query(..., description="User ID for OAuth flow")
):
    """
    Serve OAuth Web App HTML page.
    
    This page is loaded in Telegram WebView and handles the OAuth flow:
    1. Initiates OAuth by calling /oauth/{service}/initiate
    2. Redirects user to OAuth provider
    3. Receives callback and shows success/error
    
    Args:
        service: Service name (google, ticktick)
        user_id: User ID for OAuth flow
        
    Returns:
        HTMLResponse with OAuth Web App page
    """
    # Validate service
    valid_services = ["google", "ticktick"]
    if service not in valid_services:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service. Must be one of: {', '.join(valid_services)}"
        )
    
    # Load HTML template
    template_path = Path(__file__).parent / "templates" / "oauth_webapp.html"
    
    if not template_path.exists():
        raise HTTPException(
            status_code=500,
            detail="OAuth Web App template not found"
        )
    
    # Read template
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)
