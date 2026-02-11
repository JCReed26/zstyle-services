import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import AIMessage


@pytest.fixture
def mock_memory_manager():
    """Patches OpenMemory so tests don't need a running service."""
    with patch("app.core.memory.memory_manager") as mock:
        mock.get_context = MagicMock(return_value=["Previous conversation context"])
        mock.save_interaction = MagicMock()
        yield mock


@pytest.fixture
def mock_llm_response():
    """Returns a canned AIMessage for deterministic graph testing."""
    return AIMessage(content="This is a test response from the agent.")


@pytest.fixture
def mock_llm(mock_llm_response):
    """Patches ChatGoogleGenerativeAI to return canned responses."""
    mock = MagicMock()
    mock.invoke = MagicMock(return_value=mock_llm_response)
    mock.bind_tools = MagicMock(return_value=mock)
    return mock


@pytest.fixture
def test_client():
    """FastAPI TestClient for API route tests."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
