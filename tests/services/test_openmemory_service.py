import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
import aiohttp
from services.memory.openmemory_service import OpenMemoryService

@pytest.fixture
def mock_openmemory_service():
    return OpenMemoryService()

@pytest.mark.asyncio
async def test_health_check_failure(mock_openmemory_service):
    """
    Test that health check handles connection errors.
    """
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Simulate connection error
        mock_get.side_effect = aiohttp.ClientConnectorError(
            connection_key=MagicMock(),
            os_error=OSError("Connection refused")
        )
        
        # We expect it to return False, not raise
        result = await mock_openmemory_service.health_check()
        assert result is False

@pytest.mark.asyncio
async def test_add_memory_success(mock_openmemory_service):
    """
    Test add_memory success path.
    """
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"id": "mem-123", "status": "created"}
        mock_response.__aenter__.return_value = mock_response
        mock_post.return_value = mock_response

        result = await mock_openmemory_service.add_memory("user123", "content", {"tag": "test"})
        
        assert result["id"] == "mem-123"
        mock_post.assert_called_once()
        # Verify URL and JSON payload
        args, kwargs = mock_post.call_args
        assert "/api/memories" in args[0]
        assert kwargs["json"]["user_id"] == "user123"

@pytest.mark.asyncio
async def test_search_memories_success(mock_openmemory_service):
    """
    Test search_memories success path.
    """
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"id": "mem-1", "content": "match"}]
        mock_response.__aenter__.return_value = mock_response
        mock_get.return_value = mock_response

        result = await mock_openmemory_service.search_memories("user123", "query")
        
        assert len(result) == 1
        assert result[0]["content"] == "match"
        mock_get.assert_called_once()
