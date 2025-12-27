"""
OpenMemory Service Integration

This module handles the OpenMemory service integration directly using the openmemory-py SDK.
It runs locally and stores data in a SQLite database.
"""
import os
import logging
from typing import Dict, Any, List, Optional
# The installed package exposes 'Memory' not 'OpenMemory'
from openmemory import Memory

logger = logging.getLogger(__name__)

class OpenMemoryService:
    def __init__(self, db_path: str = "./zstyle_memory.db"):
        """
        Initialize the OpenMemory service client in local mode.
        
        Args:
            db_path: Path to the SQLite database file for memory storage.
        """
        # Configure OpenMemory via environment variables as per its config system
        # Set DB URL
        db_url = f"sqlite:///{os.path.abspath(db_path)}"
        os.environ["OM_DB_URL"] = db_url
        
        # Check for OpenAI key, but default to synthetic if not found or empty
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if openai_key:
            logger.info("Initializing OpenMemory with OpenAI embeddings")
            os.environ["OM_EMBED_KIND"] = "openai"
        else:
            logger.info("Initializing OpenMemory with Synthetic (Local) embeddings")
            os.environ["OM_EMBED_KIND"] = "synthetic"

        try:
            self.mem = Memory()
        except Exception as e:
            logger.error(f"Failed to initialize OpenMemory: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if the OpenMemory service is initialized and functional.
        """
        return self.mem is not None

    async def add_memory(
        self, 
        user_id: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a memory to OpenMemory.
        
        Args:
            user_id: The user ID to associate the memory with.
            content: The text content of the memory.
            metadata: Optional metadata (tags, etc.)
            
        Returns:
            The added memory object.
        """
        tags = (metadata or {}).pop("tags", [])
        meta = metadata if metadata else {}
        if "tags" in meta:
            del meta["tags"]
        
        try:
            # Memory.add is async - user_id is positional, tags/meta are kwargs
            result = await self.mem.add(
                content,
                user_id=user_id,
                tags=tags if tags else None,
                meta=meta if meta else None
            )
            return result
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise RuntimeError(f"Failed to add memory: {e}")

    async def search_memories(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for memories relevant to a query.
        
        Args:
            user_id: The user ID to search within.
            query: The search query text.
            limit: Max number of results.
            
        Returns:
            List of matching memory objects.
        """
        try:
            # Memory.search is async - user_id is a parameter, not in filters
            results = await self.mem.search(
                query,
                user_id=user_id,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            raise RuntimeError(f"Failed to search memories: {e}")

# Global instance
try:
    openmemory_service = OpenMemoryService()
except Exception as e:
    logger.error(f"Failed to create global OpenMemoryService instance: {e}")
    openmemory_service = None
