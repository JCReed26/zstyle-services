"""
Integration tests for OpenMemoryADKService.

Following TDD principles - these tests verify ADK interface compliance.
Tests use mocked OpenMemoryClient to verify service behavior.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import will fail until we implement OpenMemoryADKService
# This is expected in TDD - tests first, then implementation
try:
    from services.openmemory_adk_service import OpenMemoryADKService
    from google.adk.memory import BaseMemoryService
except ImportError:
    OpenMemoryADKService = None
    BaseMemoryService = None


@pytest.fixture
def mock_openmemory_client():
    """Mock OpenMemoryClient for testing."""
    mock_client = AsyncMock()
    mock_client.store_memory = AsyncMock(return_value="mem1")
    mock_client.search_memories = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def openmemory_adk_service(mock_openmemory_client):
    """Create OpenMemoryADKService instance for testing."""
    if OpenMemoryADKService is None:
        pytest.skip("OpenMemoryADKService not yet implemented")
    
    with patch('services.openmemory_adk_service.OpenMemoryClient', return_value=mock_openmemory_client):
        service = OpenMemoryADKService()
        return service


def test_implements_base_memory_service(openmemory_adk_service):
    """Test that OpenMemoryADKService implements BaseMemoryService."""
    if BaseMemoryService is None:
        pytest.skip("BaseMemoryService not available")
    
    assert isinstance(openmemory_adk_service, BaseMemoryService)


@pytest.mark.asyncio
async def test_add_session_to_memory(openmemory_adk_service, mock_openmemory_client):
    """Test adding session to memory."""
    # Create a mock session object
    mock_session = MagicMock()
    mock_session.user_id = "user123"
    mock_session.id = "session456"
    mock_session.messages = [
        MagicMock(role="user", content="Hello"),
        MagicMock(role="assistant", content="Hi there!")
    ]
    
    await openmemory_adk_service.add_session_to_memory(mock_session)
    
    # Verify store_memory was called
    mock_openmemory_client.store_memory.assert_called_once()
    call_args = mock_openmemory_client.store_memory.call_args
    
    assert call_args[0][0] == "user123"  # user_id
    assert "session456" in call_args[0][1]  # content should include session ID
    assert call_args[1]["metadata"] is not None  # metadata should be provided


@pytest.mark.asyncio
async def test_add_session_to_memory_formats_content(openmemory_adk_service, mock_openmemory_client):
    """Test that session content is formatted correctly."""
    mock_session = MagicMock()
    mock_session.user_id = "user1"
    mock_session.id = "sess1"
    mock_session.messages = [
        MagicMock(role="user", content="Question"),
        MagicMock(role="assistant", content="Answer")
    ]
    
    await openmemory_adk_service.add_session_to_memory(mock_session)
    
    call_args = mock_openmemory_client.store_memory.call_args
    content = call_args[0][1]
    
    # Content should include session information
    assert "sess1" in content or "session" in content.lower()


@pytest.mark.asyncio
async def test_search_memory_with_results(openmemory_adk_service, mock_openmemory_client):
    """Test searching memory with results."""
    # Mock search results
    mock_openmemory_client.search_memories.return_value = [
        {"id": "mem1", "content": "First memory", "metadata": {}},
        {"id": "mem2", "content": "Second memory", "metadata": {}}
    ]
    
    result = await openmemory_adk_service.search_memory("zstyle-bridge", "user1", "test query")
    
    # Verify search_memories was called
    mock_openmemory_client.search_memories.assert_called_once_with("user1", "test query")
    
    # Result should be a formatted string
    assert result is not None
    assert isinstance(result, str)
    assert "First memory" in result
    assert "Second memory" in result


@pytest.mark.asyncio
async def test_search_memory_empty_results(openmemory_adk_service, mock_openmemory_client):
    """Test searching memory with no results returns None."""
    mock_openmemory_client.search_memories.return_value = []
    
    result = await openmemory_adk_service.search_memory("zstyle-bridge", "user1", "nonexistent")
    
    assert result is None


@pytest.mark.asyncio
async def test_search_memory_formats_results(openmemory_adk_service, mock_openmemory_client):
    """Test that search results are formatted correctly for ADK."""
    mock_openmemory_client.search_memories.return_value = [
        {"id": "mem1", "content": "Content 1"},
        {"id": "mem2", "content": "Content 2"}
    ]
    
    result = await openmemory_adk_service.search_memory("app", "user1", "query")
    
    # Should be a string with both contents
    assert "Content 1" in result
    assert "Content 2" in result


@pytest.mark.asyncio
async def test_search_memory_handles_client_errors(openmemory_adk_service, mock_openmemory_client):
    """Test that client errors are propagated."""
    import httpx
    mock_openmemory_client.search_memories.side_effect = httpx.HTTPStatusError(
        "Server Error",
        request=MagicMock(),
        response=MagicMock()
    )
    
    with pytest.raises(httpx.HTTPStatusError):
        await openmemory_adk_service.search_memory("app", "user1", "query")
