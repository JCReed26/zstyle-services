import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.memory.openmemory_service import OpenMemoryService

@pytest.fixture
def mock_openmemory_instance():
    # Patch the Memory class where it is imported in the service module
    with patch("services.memory.openmemory_service.Memory") as mock_cls:
        instance = mock_cls.return_value
        # Make add and search async mocks
        instance.add = AsyncMock()
        instance.search = AsyncMock()
        yield instance

@pytest.fixture
def service(mock_openmemory_instance):
    return OpenMemoryService()

@pytest.mark.asyncio
async def test_health_check_success(service, mock_openmemory_instance):
    """
    Test health check returns True when mem is initialized.
    """
    result = await service.health_check()
    assert result is True

@pytest.mark.asyncio
async def test_add_memory_success(service, mock_openmemory_instance):
    """
    Test add_memory success path.
    """
    mock_openmemory_instance.add.return_value = {"id": "mem-123", "status": "created"}

    result = await service.add_memory("user123", "content", {"tags": ["test"], "other": "meta"})
    
    assert result["id"] == "mem-123"
    mock_openmemory_instance.add.assert_called_once()
    
    # Verify arguments - content is positional, user_id and others are kwargs
    args, kwargs = mock_openmemory_instance.add.call_args
    assert args[0] == "content"  # First positional arg
    assert kwargs["user_id"] == "user123"
    assert kwargs["tags"] == ["test"]
    assert kwargs["meta"] == {"other": "meta"}

@pytest.mark.asyncio
async def test_search_memories_success(service, mock_openmemory_instance):
    """
    Test search_memories success path.
    """
    mock_openmemory_instance.search.return_value = [{"id": "mem-1", "content": "match"}]

    result = await service.search_memories("user123", "query")
    
    assert len(result) == 1
    assert result[0]["content"] == "match"
    mock_openmemory_instance.search.assert_called_once()
    
    # Verify arguments - query is positional, user_id and limit are kwargs
    args, kwargs = mock_openmemory_instance.search.call_args
    assert args[0] == "query"  # First positional arg
    assert kwargs["user_id"] == "user123"
    assert kwargs["limit"] == 5
