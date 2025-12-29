"""
Auth Service

Single responsibility: Get tokens for services.
Handles refresh, expiration, everything.
Agents never call this directly.
"""
import os
import logging
import requests
from typing import Optional
from datetime import datetime, timedelta, timezone

from database.core import AsyncSessionLocal
from database.models import Credential, CredentialType
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for retrieving authentication tokens.
    
    Agents NEVER import or use this directly.
    Only agent wrappers (TickTickAgentTool, GmailAgentTool, etc.) call this.
    """
    
    @staticmethod
    async def get_ticktick_token(user_id: str) -> Optional[str]:
        """
        Get TickTick access token for user.
        
        Handles token refresh automatically if expired.
        
        Args:
            user_id: User ID
            
        Returns:
            Access token string or None if not available
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Credential).where(
                    and_(
                        Credential.user_id == user_id,
                        Credential.credential_type == CredentialType.TICKTICK_TOKEN,
                        Credential.is_active == True
                    )
                )
            )
            cred = result.scalar_one_or_none()
            
            if not cred:
                return None
            
            # Check if expired and refresh if needed
            if cred.is_expired() and cred.refresh_token:
                refreshed = await AuthService._refresh_ticktick_token(user_id, cred.refresh_token)
                if refreshed:
                    # Re-fetch after refresh
                    result = await db.execute(
                        select(Credential).where(
                            and_(
                                Credential.user_id == user_id,
                                Credential.credential_type == CredentialType.TICKTICK_TOKEN,
                                Credential.is_active == True
                            )
                        )
                    )
                    cred = result.scalar_one_or_none()
            
            if cred and not cred.is_expired():
                return cred.token_value
        
        return None
    
    @staticmethod
    async def get_google_token(user_id: str) -> Optional[str]:
        """
        Get Google OAuth token for user.
        
        Handles token refresh automatically if expired.
        
        Args:
            user_id: User ID
            
        Returns:
            Access token string or None if not available
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Credential).where(
                    and_(
                        Credential.user_id == user_id,
                        Credential.credential_type == CredentialType.GOOGLE_OAUTH,
                        Credential.is_active == True
                    )
                )
            )
            cred = result.scalar_one_or_none()
            
            if not cred:
                return None
            
            # Check if expired and refresh if needed
            if cred.is_expired() and cred.refresh_token:
                refreshed = await AuthService._refresh_google_token(user_id, cred.refresh_token)
                if refreshed:
                    # Re-fetch after refresh
                    result = await db.execute(
                        select(Credential).where(
                            and_(
                                Credential.user_id == user_id,
                                Credential.credential_type == CredentialType.GOOGLE_OAUTH,
                                Credential.is_active == True
                            )
                        )
                    )
                    cred = result.scalar_one_or_none()
            
            if cred and not cred.is_expired():
                return cred.token_value
        
        return None
    
    @staticmethod
    async def _refresh_google_token(user_id: str, refresh_token: str) -> bool:
        """Refresh Google access token using refresh token."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not all([client_id, client_secret]):
            return False
        
        try:
            response = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            })
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            if not access_token:
                return False
            
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
            
            # Update credential in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Credential).where(
                        Credential.user_id == user_id,
                        Credential.credential_type == CredentialType.GOOGLE_OAUTH
                    )
                )
                cred = result.scalar_one_or_none()
                
                if cred:
                    cred.token_value = access_token
                    cred.expires_at = expires_at
                    if cred.extra_data:
                        cred.extra_data.update(token_data)
                    else:
                        cred.extra_data = token_data
                    await db.commit()
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to refresh Google token for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def _refresh_ticktick_token(user_id: str, refresh_token: str) -> bool:
        """Refresh TickTick access token using refresh token."""
        client_id = os.getenv("TICKTICK_CLIENT_ID")
        client_secret = os.getenv("TICKTICK_CLIENT_SECRET")
        
        if not all([client_id, client_secret]):
            return False
        
        try:
            response = requests.post("https://ticktick.com/oauth/token", data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            })
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            if not access_token:
                return False
            
            expires_at = None
            if "expires_in" in token_data:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
            
            # Update credential in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Credential).where(
                        Credential.user_id == user_id,
                        Credential.credential_type == CredentialType.TICKTICK_TOKEN
                    )
                )
                cred = result.scalar_one_or_none()
                
                if cred:
                    cred.token_value = access_token
                    cred.expires_at = expires_at
                    if "refresh_token" in token_data:
                        cred.refresh_token = token_data["refresh_token"]
                    if cred.extra_data:
                        cred.extra_data.update(token_data)
                    else:
                        cred.extra_data = token_data
                    await db.commit()
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to refresh TickTick token for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def store_google_token(user_id: str, access_token: str, refresh_token: Optional[str], expires_at: Optional[datetime], extra_data: dict):
        """
        Store Google OAuth tokens in database.
        
        Called by OAuthService after successful OAuth flow.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.GOOGLE_OAUTH
                )
            )
            existing_cred = result.scalar_one_or_none()
            
            if existing_cred:
                existing_cred.token_value = access_token
                existing_cred.expires_at = expires_at
                existing_cred.extra_data = extra_data
                if refresh_token:
                    existing_cred.refresh_token = refresh_token
            else:
                new_cred = Credential(
                    user_id=user_id,
                    credential_type=CredentialType.GOOGLE_OAUTH,
                    token_value=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    extra_data=extra_data
                )
                db.add(new_cred)
            
            await db.commit()
    
    @staticmethod
    async def store_ticktick_token(user_id: str, access_token: str, refresh_token: Optional[str], expires_at: Optional[datetime], extra_data: dict):
        """
        Store TickTick OAuth tokens in database.
        
        Called by OAuthService after successful OAuth flow.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Credential).where(
                    Credential.user_id == user_id,
                    Credential.credential_type == CredentialType.TICKTICK_TOKEN
                )
            )
            existing_cred = result.scalar_one_or_none()
            
            if existing_cred:
                existing_cred.token_value = access_token
                existing_cred.expires_at = expires_at
                existing_cred.extra_data = extra_data
                if refresh_token:
                    existing_cred.refresh_token = refresh_token
            else:
                new_cred = Credential(
                    user_id=user_id,
                    credential_type=CredentialType.TICKTICK_TOKEN,
                    token_value=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    extra_data=extra_data
                )
                db.add(new_cred)
            
            await db.commit()


# Singleton instance
auth_service = AuthService()

