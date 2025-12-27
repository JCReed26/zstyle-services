import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any

# Add project root to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.adk.tools import ToolContext

@pytest.fixture
def mock_db_session():
    """
    Creates a mock database session that simulates AsyncSession.
    """
    session = AsyncMock()
    
    # Setup common methods
    session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [], first=lambda: None, one_or_none=lambda: None)))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    
    # Mock the context manager behavior (async with session as db:)
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    
    return session

@pytest.fixture(autouse=True)
def patch_db_session(monkeypatch, mock_db_session):
    """
    Automatically patch AsyncSessionLocal in database.core for all tests.
    """
    # Create a mock factory that returns our mock session
    mock_factory = MagicMock(return_value=mock_db_session)
    
    # We also need to handle the case where AsyncSessionLocal() is called directly as a context manager
    # i.e., async with AsyncSessionLocal() as db:
    mock_factory.__aenter__.return_value = mock_db_session
    mock_factory.__aexit__.return_value = None
    
    import database.core as engine_module
    monkeypatch.setattr(engine_module, "AsyncSessionLocal", mock_factory)
    return mock_db_session

@pytest.fixture
def mock_tool_context():
    """
    Creates a mock ToolContext with a predefined user_id state.
    """
    context = MagicMock(spec=ToolContext)
    context.state = {"user_id": "test-user-123"}
    return context

