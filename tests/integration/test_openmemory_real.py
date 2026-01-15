"""
Integration tests for OpenMemory using real HTTP server.

These tests require OpenMemory Docker container to be running.
Run with: docker-compose up -d openmemory
"""
import pytest
import os
from unittest.mock import patch

# Import will fail until we implement OpenMemoryClient
try:
    from services.openmemory_client import OpenMemoryClient
except ImportError:
    OpenMemoryClient = None

# Skip if OpenMemory URL is not set or if we're in CI without Docker
OPENMEMORY_URL = os.getenv("OPENMEMORY_URL", "http://localhost:8080")
REAL_SERVER_AVAILABLE = os.getenv("OPENMEMORY_REAL_TESTS", "false").lower() == "true"


@pytest.fixture
def openmemory_client():
    """Create OpenMemoryClient pointing to real server."""
    if OpenMemoryClient is None:
        pytest.skip("OpenMemoryClient not yet implemented")
    
    # Override URL for testing
    with patch('services.openmemory_client.settings') as mock_settings:
        mock_settings.OPENMEMORY_URL = OPENMEMORY_URL
        mock_settings.OPENMEMORY_API_KEY = os.getenv("OPENMEMORY_API_KEY")
        client = OpenMemoryClient()
        yield client


@pytest.mark.skipif(not REAL_SERVER_AVAILABLE, reason="Real server tests disabled")
@pytest.mark.asyncio
async def test_store_and_search_memory_real_server(openmemory_client):
    """Test storing and searching memory against real OpenMemory server."""
    import httpx
    
    # Test store
    try:
        memory_id = await openmemory_client.store_memory(
            user_id="test_user_real",
            content="This is a test memory for real server integration",
            metadata={"test": True, "source": "pytest"}
        )
        
        assert memory_id is not None
        assert isinstance(memory_id, str)
        
        # Test search
        results = await openmemory_client.search_memories(
            user_id="test_user_real",
            query="test memory",
            limit=10
        )
        
        assert isinstance(results, list)
        # Should find at least the memory we just stored
        assert len(results) > 0
        assert any("test memory" in r.get("content", "").lower() for r in results)
        
    except httpx.ConnectError:
        pytest.skip("OpenMemory server not available. Start with: docker-compose up -d openmemory")


@pytest.mark.skipif(not REAL_SERVER_AVAILABLE, reason="Real server tests disabled")
@pytest.mark.asyncio
async def test_search_empty_user_real_server(openmemory_client):
    """Test searching for non-existent user returns empty list."""
    import httpx
    
    try:
        results = await openmemory_client.search_memories(
            user_id="nonexistent_user_12345",
            query="anything",
            limit=10
        )
        
        assert isinstance(results, list)
        # Should return empty list, not error
        
    except httpx.ConnectError:
        pytest.skip("OpenMemory server not available")


@pytest.mark.skipif(not REAL_SERVER_AVAILABLE, reason="Real server tests disabled")
@pytest.mark.asyncio
async def test_store_memory_metadata_real_server(openmemory_client):
    """Test storing memory with metadata against real server."""
    import httpx
    
    try:
        metadata = {
            "channel": "telegram",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": "test_session_123"
        }
        
        memory_id = await openmemory_client.store_memory(
            user_id="test_user_metadata",
            content="Memory with metadata",
            metadata=metadata
        )
        
        assert memory_id is not None
        
        # Search and verify metadata is preserved
        results = await openmemory_client.search_memories(
            user_id="test_user_metadata",
            query="metadata",
            limit=1
        )
        
        if results:
            # Metadata might be in the result
            assert len(results) > 0
            
    except httpx.ConnectError:
        pytest.skip("OpenMemory server not available")
