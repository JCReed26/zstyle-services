"""
OpenMemory ADK Memory Service - Simple integration.

Implements ADK BaseMemoryService using OpenMemory as the memory brain.
No session management - just stores/retrieves memories by user_id.
"""
import logging
from typing import List, Optional
from google.adk.memory import BaseMemoryService
from google.adk.sessions import Session
from services.openmemory_client import get_openmemory_client
from database.availability import is_database_available

logger = logging.getLogger(__name__)


class OpenMemoryADKService(BaseMemoryService):
    """ADK Memory Service using OpenMemory as the memory brain."""
    
    def __init__(self):
        """Initialize service."""
        self.client = get_openmemory_client()
        logger.info("OpenMemoryADKService initialized")
    
    async def add_session_to_memory(
        self,
        session: Session,
        content: Optional[str] = None
    ) -> None:
        """Store conversation content to OpenMemory (no session tracking)."""
        try:
            # Get user_id from session metadata
            user_id = session.metadata.get("user_id") if session.metadata else None
            
            # Quick validation: user should exist in database
            if user_id and is_database_available():
                from database.engine import AsyncSessionLocal
                from database.models import User
                from sqlalchemy import select
                if AsyncSessionLocal:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(select(User).where(User.id == user_id))
                        if not result.scalar_one_or_none():
                            logger.warning(f"User {user_id} not found, skipping memory storage")
                            return
            
            # Extract conversation content (last messages)
            if not content:
                content = self._extract_content(session)
            
            # Skip if no content
            if not content:
                return
            
            # Store to OpenMemory (the memory brain)
            result = await self.client.store(
                content=content,
                user_id=user_id,
                tags=["agent_memory"],
                metadata={
                    "app_name": session.app_name
                }
            )
            
            if result.get("status") == "success":
                logger.debug(f"Stored memory for user {user_id}")
            else:
                logger.warning(f"Failed to store memory: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error storing memory: {e}", exc_info=True)
            # Don't raise - memory failures shouldn't break agent
    
    async def search_memory(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[str]:
        """Search memories from OpenMemory brain."""
        try:
            # Search OpenMemory
            results = await self.client.search(query, user_id=user_id, limit=limit)
            
            # Extract content strings
            return [
                r.get("content", r.get("text", str(r)))
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error searching memory: {e}", exc_info=True)
            return []
    
    def _extract_content(self, session: Session) -> str:
        """Extract conversation content from session."""
        parts = []
        if hasattr(session, 'messages') and session.messages:
            # Get last messages for context
            for msg in session.messages[-10:]:
                role = getattr(msg, 'role', 'unknown')
                content = getattr(msg, 'content', '')
                if isinstance(content, list):
                    content = ' '.join(str(c) for c in content)
                if content:
                    parts.append(f"{role}: {content}")
        return "\n".join(parts) if parts else ""
