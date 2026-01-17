"""
OAuth State Service

High-level service for managing OAuth state tokens.
Provides business logic layer over OAuthStateRepository.
"""
import secrets
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from database.engine import AsyncSessionLocal
from database.repositories import OAuthStateRepository


class OAuthStateService:
    """
    Service for managing OAuth state tokens.
    
    Handles generation, validation, and consumption of OAuth state tokens
    for CSRF protection in OAuth flows.
    """
    
    STATE_EXPIRATION_MINUTES = 10
    
    def _get_session_context(self, session: Optional[AsyncSession] = None):
        """
        Get a database session context manager.
        
        Args:
            session: Optional existing session to use
            
        Returns:
            Context manager that yields an AsyncSession
        """
        if session is not None:
            @asynccontextmanager
            async def _noop_context():
                yield session
            return _noop_context()
        else:
            return AsyncSessionLocal()
    
    async def create_state(
        self,
        user_id: str,
        service: str,
        session: Optional[AsyncSession] = None
    ) -> str:
        """
        Create a new OAuth state token.
        
        Generates a cryptographically random state token and stores it
        in the database with expiration tracking.
        
        Args:
            user_id: User ID for this OAuth flow
            service: Service name (e.g., "google", "ticktick")
            session: Optional database session
            
        Returns:
            State token string
        """
        # Generate cryptographically random state token
        state_token = secrets.token_urlsafe(32)
        
        async with self._get_session_context(session) as db:
            repo = OAuthStateRepository(db)
            await repo.create(
                state_token=state_token,
                user_id=user_id,
                service=service,
                expiration_minutes=self.STATE_EXPIRATION_MINUTES
            )
        
        return state_token
    
    async def validate_and_consume(
        self,
        state_token: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[dict]:
        """
        Validate and consume an OAuth state token.
        
        Checks if token exists, is not expired, and hasn't been consumed.
        Then marks it as consumed (single-use).
        
        Args:
            state_token: State token to validate
            session: Optional database session
            
        Returns:
            Dictionary with user_id and service if valid, None otherwise
        """
        async with self._get_session_context(session) as db:
            repo = OAuthStateRepository(db)
            
            try:
                oauth_state = await repo.consume_token(state_token)
                
                if not oauth_state:
                    return None
                
                return {
                    "user_id": oauth_state.user_id,
                    "service": oauth_state.service
                }
            except ValueError:
                # Token already consumed or expired
                return None
    
    async def cleanup_expired(
        self,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Clean up expired OAuth states.
        
        Args:
            session: Optional database session
            
        Returns:
            Number of states deleted
        """
        async with self._get_session_context(session) as db:
            repo = OAuthStateRepository(db)
            return await repo.cleanup_expired()


# Singleton instance
_oauth_state_service: Optional[OAuthStateService] = None


def get_oauth_state_service() -> OAuthStateService:
    """Get singleton OAuthStateService instance."""
    global _oauth_state_service
    if _oauth_state_service is None:
        _oauth_state_service = OAuthStateService()
    return _oauth_state_service


# Convenience alias
oauth_state_service = get_oauth_state_service()
