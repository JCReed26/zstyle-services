"""
OAuth Utility Functions

Helper functions for OAuth flow configuration.
"""
from app.config import settings


def get_redirect_uri(service: str) -> str:
    """
    Get redirect URI for OAuth service.
    
    Uses OAUTH_BASE_URL if set, otherwise falls back to localhost.
    This allows different configurations for development and production.
    
    Args:
        service: Service name (e.g., "google", "ticktick")
        
    Returns:
        Full redirect URI (e.g., "https://api.example.com/oauth/google/callback")
    """
    if settings.OAUTH_BASE_URL:
        base_url = settings.OAUTH_BASE_URL.rstrip('/')
    else:
        # Fallback to localhost for development
        base_url = f"http://localhost:{settings.PORT}"
    
    return f"{base_url}/oauth/{service}/callback"
