"""
ADK Credential Loader Service

Pre-loads user credentials into ToolContext.state when sessions start.
This ensures credentials are available throughout the conversation.

Follows existing patterns from:
- services/google_credential_provider.py for Google credential loading
- channels/router.py for session state access
"""
import logging
from typing import Optional, Dict, Any

# Try to import ToolContext - may not be available in all ADK versions
try:
    from google.adk.tools import ToolContext
except ImportError:
    ToolContext = None

from services.credential_service import credential_service
from services.google_credential_provider import get_google_credential_provider

logger = logging.getLogger(__name__)


class ADKCredentialLoader:
    """
    Loads credentials into ToolContext.state for ADK tools.
    
    This service ensures that when a user starts a conversation,
    their credentials are pre-loaded into tool_context.state so
    tools can access them immediately without database queries.
    """
    
    async def load_user_credentials(
        self,
        user_id: str,
        tool_context: Optional[Any] = None,
        services: Optional[list[str]] = None
    ) -> Dict[str, bool]:
        """
        Pre-load credentials for user into tool_context.state.
        
        Args:
            user_id: User ID
            tool_context: ADK ToolContext or object with state attribute
            services: List of services to load (default: ["google", "ticktick"])
            
        Returns:
            Dictionary mapping service names to success status
        """
        if not tool_context or not hasattr(tool_context, 'state') or not tool_context.state:
            logger.debug(f"No tool_context.state available for user {user_id}")
            return {}
        
        services = services or ["google", "ticktick"]
        results = {}
        
        for service in services:
            try:
                cred_key = f"auth:{service}:{user_id}"
                
                # Check if already loaded
                if cred_key in tool_context.state:
                    logger.debug(f"Credentials already loaded for {service}:{user_id}")
                    results[service] = True
                    continue
                
                # Load credentials based on service
                if service == "google":
                    credential_provider = get_google_credential_provider()
                    creds = await credential_provider.get_credentials_for_user(
                        user_id,
                        tool_context,
                        service="google"
                    )
                    if creds:
                        # Credentials are already cached in tool_context.state by get_credentials_for_user
                        results[service] = True
                        logger.info(f"Pre-loaded Google credentials for user {user_id}")
                    else:
                        results[service] = False
                        logger.debug(f"No Google credentials found for user {user_id}")
                
                elif service == "ticktick":
                    # Load TickTick credentials
                    creds = await credential_service.get_credentials(user_id, "ticktick")
                    if creds:
                        # Store raw format in state (TickTick tools handle their own formatting)
                        tool_context.state[cred_key] = creds
                        results[service] = True
                        logger.info(f"Pre-loaded TickTick credentials for user {user_id}")
                    else:
                        results[service] = False
                        logger.debug(f"No TickTick credentials found for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to load {service} credentials for user {user_id}: {e}", exc_info=True)
                results[service] = False
        
        return results


# Singleton instance
_adk_credential_loader: Optional[ADKCredentialLoader] = None


def get_adk_credential_loader() -> ADKCredentialLoader:
    """Get singleton ADKCredentialLoader instance."""
    global _adk_credential_loader
    if _adk_credential_loader is None:
        _adk_credential_loader = ADKCredentialLoader()
    return _adk_credential_loader
