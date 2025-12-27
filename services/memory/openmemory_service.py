"""
OpenMemory Service Integration

This module handles communication with the OpenMemory service running via Docker.
It provides methods to add and retrieve memories.
"""
import os
import aiohttp
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class OpenMemoryService:
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the OpenMemory service client.
        
        Args:
            base_url: The URL of the OpenMemory service. 
                      Defaults to OPENMEMORY_URL env var or http://localhost:3000
        """
        self.base_url = base_url or os.getenv("OPENMEMORY_URL", "http://localhost:3000")

    async def health_check(self) -> bool:
        """
        Check if the OpenMemory service is reachable.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Assuming /health or / root endpoint exists
                async with session.get(f"{self.base_url}/") as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"OpenMemory health check failed: {e}")
            return False

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
            The response from OpenMemory.
        """
        payload = {
            "user_id": user_id,
            "content": content,
            "metadata": metadata or {}
        }
        
        async with aiohttp.ClientSession() as session:
            # Adjust endpoint based on OpenMemory API docs
            # Placeholder: /api/memories
            async with session.post(f"{self.base_url}/api/memories", json=payload) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise RuntimeError(f"Failed to add memory: {response.status} - {text}")
                return await response.json()

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
        params = {
            "user_id": user_id,
            "query": query,
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            # Adjust endpoint based on OpenMemory API docs
            # Placeholder: /api/memories/search
            async with session.get(f"{self.base_url}/api/memories/search", params=params) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise RuntimeError(f"Failed to search memories: {response.status} - {text}")
                return await response.json()

# Global instance
openmemory_service = OpenMemoryService()
