"""
Unit tests for OpenMemoryClient.

Following TDD principles - these tests are written before implementation.
Tests use mocked HTTP responses to verify client behavior.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import will fail until we implement OpenMemoryClient
# This is expected in TDD - tests first, then implementation
try:
    from services.openmemory_client import OpenMemoryClient, OpenMemoryError
except ImportError:
    OpenMemoryClient = None
    OpenMemoryError = None


@pytest.fixture
def mock_settings():
    """Mock settings for OpenMemoryClient initialization."""
    with patch('services.openmemory_client.settings') as mock_settings:
        mock_settings.OPENMEMORY_URL = "http://test-openmemory:8080"
        mock_settings.OPENMEMORY_API_KEY = "test-api-key"
        yield mock_settings


@pytest.fixture
def openmemory_client(mock_settings):
    """Create OpenMemoryClient instance for testing."""
    if OpenMemoryClient is None:
        pytest.skip("OpenMemoryClient not yet implemented")
    return OpenMemoryClient()


@pytest.mark.asyncio
async def test_store_memory_success(openmemory_client):
    """Test successful memory storage."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "mem1", "user_id": "user1"}
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(openmemory_client._client, 'post', return_value=mock_response) as mock_post:
        result = await openmemory_client.store_memory("user1", "test content")
        
        assert result == "mem1"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test-openmemory:8080/api/memories"
        assert call_args[1]["json"]["user_id"] == "user1"
        assert call_args[1]["json"]["content"] == "test content"
        assert call_args[1]["json"]["metadata"] == {}
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"


@pytest.mark.asyncio
async def test_store_memory_with_metadata(openmemory_client):
    """Test storing memory with custom metadata."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "mem2"}
    mock_response.raise_for_status = MagicMock()
    
    metadata = {"source": "telegram", "timestamp": "2024-01-01"}
    
    with patch.object(openmemory_client._client, 'post', return_value=mock_response) as mock_post:
        result = await openmemory_client.store_memory("user1", "content", metadata=metadata)
        
        assert result == "mem2"
        call_args = mock_post.call_args
        assert call_args[1]["json"]["metadata"] == metadata


@pytest.mark.asyncio
async def test_store_memory_http_error(openmemory_client):
    """Test handling HTTP errors during memory storage."""
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error",
        request=MagicMock(),
        response=mock_response
    )
    
    with patch.object(openmemory_client._client, 'post', return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            await openmemory_client.store_memory("user1", "content")


@pytest.mark.asyncio
async def test_store_memory_network_error(openmemory_client):
    """Test handling network errors."""
    with patch.object(openmemory_client._client, 'post', side_effect=httpx.NetworkError("Connection failed")):
        with pytest.raises(httpx.NetworkError):
            await openmemory_client.store_memory("user1", "content")


@pytest.mark.asyncio
async def test_store_memory_no_api_key(openmemory_client):
    """Test that client works without API key."""
    # Temporarily remove API key
    original_key = openmemory_client.api_key
    openmemory_client.api_key = None
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "mem3"}
    mock_response.raise_for_status = MagicMock()
    
    try:
        with patch.object(openmemory_client._client, 'post', return_value=mock_response) as mock_post:
            await openmemory_client.store_memory("user1", "content")
            call_args = mock_post.call_args
            # Should not have Authorization header when no API key
            assert "Authorization" not in call_args[1].get("headers", {})
    finally:
        openmemory_client.api_key = original_key


@pytest.mark.asyncio
async def test_search_memories_success(openmemory_client):
    """Test successful memory search."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": "mem1", "content": "test content 1", "metadata": {}},
        {"id": "mem2", "content": "test content 2", "metadata": {"source": "telegram"}}
    ]
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(openmemory_client._client, 'get', return_value=mock_response) as mock_get:
        results = await openmemory_client.search_memories("user1", "test query", limit=10)
        
        assert len(results) == 2
        assert results[0]["id"] == "mem1"
        assert results[1]["id"] == "mem2"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "user_id=user1" in str(call_args[0][0])
        assert "query=test+query" in str(call_args[0][0])
        assert "limit=10" in str(call_args[0][0])


@pytest.mark.asyncio
async def test_search_memories_empty_results(openmemory_client):
    """Test search with no results."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(openmemory_client._client, 'get', return_value=mock_response):
        results = await openmemory_client.search_memories("user1", "nonexistent")
        
        assert results == []
        assert len(results) == 0


@pytest.mark.asyncio
async def test_search_memories_respects_limit(openmemory_client):
    """Test that search respects limit parameter."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": f"mem{i}"} for i in range(5)]
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(openmemory_client._client, 'get', return_value=mock_response) as mock_get:
        results = await openmemory_client.search_memories("user1", "query", limit=3)
        
        call_args = mock_get.call_args
        assert "limit=3" in str(call_args[0][0])


@pytest.mark.asyncio
async def test_search_memories_default_limit(openmemory_client):
    """Test that search uses default limit of 10."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(openmemory_client._client, 'get', return_value=mock_response) as mock_get:
        await openmemory_client.search_memories("user1", "query")
        
        call_args = mock_get.call_args
        assert "limit=10" in str(call_args[0][0])


@pytest.mark.asyncio
async def test_search_memories_http_error(openmemory_client):
    """Test handling HTTP errors during search."""
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=MagicMock(),
        response=mock_response
    )
    
    with patch.object(openmemory_client._client, 'get', return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            await openmemory_client.search_memories("user1", "query")


@pytest.mark.asyncio
async def test_client_initialization():
    """Test OpenMemoryClient initialization."""
    if OpenMemoryClient is None:
        pytest.skip("OpenMemoryClient not yet implemented")
    
    with patch('services.openmemory_client.settings') as mock_settings:
        mock_settings.OPENMEMORY_URL = "http://custom:9090"
        mock_settings.OPENMEMORY_API_KEY = "custom-key"
        
        client = OpenMemoryClient()
        
        assert client.base_url == "http://custom:9090"
        assert client.api_key == "custom-key"
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)
