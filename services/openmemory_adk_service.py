"""
OpenMemory ADK Service

Implements Google ADK BaseMemoryService interface using OpenMemory HTTP server.
Enables centralized memory bank accessible by multiple agents via ADK Runner.
"""
import logging
from typing import Optional
from google.adk.memory import BaseMemoryService

from services.openmemory_client import OpenMemoryClient

logger = logging.getLogger(__name__)


class OpenMemoryADKService(BaseMemoryService):
    """
    ADK MemoryService implementation using OpenMemory HTTP server.
    
    This service implements the BaseMemoryService interface, allowing ADK Runner
    to automatically handle memory storage and retrieval. Multiple agents can
    access the same centralized memory bank via this service.
    """
    
    def __init__(self):
        """Initialize OpenMemory ADK Service."""
        super().__init__()
        self.client = OpenMemoryClient()
        logger.info("OpenMemoryADKService initialized")
    
    async def add_session_to_memory(self, session) -> None:
        """
        Add a session to memory.
        
        Implements BaseMemoryService interface. Stores session data in OpenMemory
        for later retrieval by search_memory.
        
        Args:
            session: ADK Session object with user_id, id, and messages
        """
        try:
            user_id = session.user_id
            
            # Format session data as content string
            # Include session ID and message summary for context
            content_parts = [f"Session ID: {session.id}"]
            
            if hasattr(session, 'messages') and session.messages:
                content_parts.append("Messages:")
                for msg in session.messages[-10:]:  # Last 10 messages for context
                    role = getattr(msg, 'role', 'unknown')
                    msg_content = getattr(msg, 'content', '')
                    if hasattr(msg_content, 'parts') and msg_content.parts:
                        # Handle Content object with parts
                        text_parts = []
                        for part in msg_content.parts:
                            if hasattr(part, 'text'):
                                text_parts.append(part.text)
                        msg_text = " ".join(text_parts)
                    elif isinstance(msg_content, str):
                        msg_text = msg_content
                    else:
                        msg_text = str(msg_content)
                    content_parts.append(f"{role}: {msg_text[:200]}")  # Truncate long messages
            
            content = "\n".join(content_parts)
            
            # Store metadata about the session
            metadata = {
                "session_id": session.id,
                "app_name": getattr(session, 'app_name', 'unknown'),
                "source": "adk"
            }
            
            memory_id = await self.client.store_memory(
                user_id=user_id,
                content=content,
                metadata=metadata
            )
            
            logger.debug(f"Stored session {session.id} to memory as {memory_id} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding session to memory: {e}", exc_info=True)
            # Don't raise - memory storage failures shouldn't break agent flow
            # ADK will handle gracefully
    
    async def search_memory(
        self,
        app_name: str,
        user_id: str,
        query: str
    ) -> Optional[str]:
        """
        Search memory for a user.
        
        Implements BaseMemoryService interface. Searches OpenMemory for relevant
        memories and returns formatted string for ADK consumption.
        
        Args:
            app_name: Application name (for multi-app support, if needed)
            user_id: User identifier to search within
            query: Search query string
            
        Returns:
            Formatted string with relevant memories, or None if no results
        """
        try:
            results = await self.client.search_memories(
                user_id=user_id,
                query=query,
                limit=10
            )
            
            if not results:
                logger.debug(f"No memories found for user {user_id} query '{query}'")
                return None
            
            # Format results as string for ADK
            # ADK expects a string that can be injected into context
            formatted_results = []
            for i, result in enumerate(results, 1):
                content = result.get("content", "")
                memory_id = result.get("id", "unknown")
                formatted_results.append(f"[Memory {i} (ID: {memory_id})]\n{content}")
            
            result_text = "\n\n".join(formatted_results)
            logger.debug(f"Found {len(results)} memories for user {user_id} query '{query}'")
            
            return result_text
            
        except Exception as e:
            logger.error(f"Error searching memory for user {user_id}: {e}", exc_info=True)
            # Return None on error - agent can continue without memory context
            return None
