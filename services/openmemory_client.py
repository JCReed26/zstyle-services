"""
OpenMemory Client - Simple embedding storage.

Connects to OpenMemory service for storing and retrieving embeddings.
User isolation handled by OpenMemory via metadata filtering.

Based on: https://github.com/caviraoss/openmemory
"""
import logging
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy import - use correct import path from openmemory.client to avoid langchain connector bug
try:
    from openmemory.client import Memory
except (ImportError, NameError) as e:
    logger.error(f"Failed to import Memory from openmemory.client: {e}.")
    logger.error("Please check openmemory-py version or see https://github.com/caviraoss/openmemory")
    # Set to None so we can check later
    Memory = None  # type: ignore


class OpenMemoryClient:
    """Simple client for OpenMemory embedding service."""
    
    def __init__(self):
        """Initialize OpenMemory client."""
        if Memory is None:
            raise RuntimeError(
                "Memory import failed from openmemory.client. "
                "Please check the package version or see logs for details."
            )
        # Configure Memory client for remote mode
        # See: https://github.com/caviraoss/openmemory
        if settings.OPENMEMORY_URL and settings.OPENMEMORY_URL != "http://openmemory:8080":
            # Remote mode with explicit URL
            self.client = Memory(
                mode='remote',
                url=settings.OPENMEMORY_URL,
                api_key=settings.OPENMEMORY_API_KEY
            )
            logger.info(f"OpenMemory client initialized (remote mode): {settings.OPENMEMORY_URL}")
        else:
            # Local mode (default) - uses SQLite
            self.client = Memory()
            logger.info("OpenMemory client initialized (local mode)")
    
    async def store(
        self,
        content: str,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store content as embedding in OpenMemory."""
        try:
            # Prepare metadata with user_id for filtering
            memory_metadata = metadata or {}
            if user_id:
                memory_metadata["user_id"] = user_id
            
            # Store in OpenMemory (handles embedding generation)
            # OpenMemory methods are async according to docs
            result = await self.client.add(
                content,
                user_id=user_id,
                tags=tags or [],
                metadata=memory_metadata
            )
            
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error storing memory: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    async def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search embeddings by query, filtered by user_id."""
        try:
            # Search OpenMemory (handles semantic search)
            # OpenMemory's search method is async and accepts user_id directly
            results = await self.client.search(query, user_id=user_id, limit=limit)
            
            return results
        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []


# Global singleton instance
_openmemory_client: Optional[OpenMemoryClient] = None


def get_openmemory_client() -> OpenMemoryClient:
    """Get singleton OpenMemory client instance."""
    global _openmemory_client
    if _openmemory_client is None:
        _openmemory_client = OpenMemoryClient()
    return _openmemory_client
