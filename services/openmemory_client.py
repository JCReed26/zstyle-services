"""
OpenMemory HTTP Client

HTTP client for interacting with OpenMemory HTTP server.
Provides centralized memory storage accessible by multiple agents.
"""
import logging
from typing import List, Dict, Optional, Any
import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class OpenMemoryError(Exception):
    """Base exception for OpenMemory client errors."""
    pass


class OpenMemoryClient:
    """
    HTTP client for OpenMemory server.
    
    Provides methods to store and search memories via HTTP API.
    Supports user namespacing for multi-tenant memory isolation.
    """
    
    def __init__(self):
        """
        Initialize OpenMemory client.
        
        Uses settings.OPENMEMORY_URL and settings.OPENMEMORY_API_KEY for configuration.
        """
        self.base_url = settings.OPENMEMORY_URL
        self.api_key = settings.OPENMEMORY_API_KEY
        self._client = httpx.AsyncClient(timeout=30.0)
        logger.debug(f"OpenMemoryClient initialized with URL: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including authentication if API key is present."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def store_memory(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory in OpenMemory.
        
        Args:
            user_id: User identifier (used as namespace/collection)
            content: Memory content to store
            metadata: Optional metadata dictionary
            
        Returns:
            Memory ID string
            
        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            httpx.NetworkError: If network request fails
        """
        url = f"{self.base_url}/api/memories"
        data = {
            "user_id": user_id,
            "content": content,
            "metadata": metadata or {}
        }
        
        try:
            response = await self._client.post(
                url,
                json=data,
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()
            memory_id = result.get("id")
            
            if not memory_id:
                raise OpenMemoryError(f"OpenMemory API did not return memory ID: {result}")
            
            logger.debug(f"Stored memory {memory_id} for user {user_id}")
            return memory_id
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error storing memory for user {user_id}: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"Network error storing memory for user {user_id}: {e}")
            raise
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories for a user.
        
        Args:
            user_id: User identifier to search within
            query: Search query string
            limit: Maximum number of results to return (default: 10)
            
        Returns:
            List of memory dictionaries with id, content, metadata fields
            
        Raises:
            httpx.HTTPStatusError: If HTTP request fails
            httpx.NetworkError: If network request fails
        """
        url = f"{self.base_url}/api/memories"
        params = {
            "user_id": user_id,
            "query": query,
            "limit": limit
        }
        
        try:
            response = await self._client.get(
                url,
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            results = response.json()
            
            # Ensure results is a list
            if not isinstance(results, list):
                logger.warning(f"OpenMemory API returned non-list result: {results}")
                return []
            
            logger.debug(f"Found {len(results)} memories for user {user_id} query '{query}'")
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error searching memories for user {user_id}: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"Network error searching memories for user {user_id}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
