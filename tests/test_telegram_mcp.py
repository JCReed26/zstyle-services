import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch

# Mock env for testing
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "fakehash"
os.environ["TELEGRAM_SESSION_STRING"] = "fakesession"

@pytest.fixture
def mock_client():
    with patch("services.telegram_mcp.main.TelegramClient") as MockClient:
        client_instance = MockClient.return_value
        
        # Use AsyncMock for async methods if available, else manual future
        try:
            from unittest.mock import AsyncMock
            # Mock async methods with AsyncMock which are awaitable by default
            client_instance.get_dialogs = AsyncMock(return_value=[])
            client_instance.get_me = AsyncMock(return_value=MagicMock(id=123, first_name="Test", username="testbot"))
            client_instance.get_entity = AsyncMock(return_value=MagicMock(id=123))
            client_instance.get_messages = AsyncMock(return_value=[])
            client_instance.send_message = AsyncMock(return_value=None)
        except ImportError:
            # Fallback for older python (unlikely here)
            pass
            
        yield client_instance

@pytest.mark.asyncio
async def test_get_chats_empty(mock_client):
    from services.telegram_mcp.main import get_chats
    
    # We need to ensure the global client in main.py is our mock
    with patch("services.telegram_mcp.main.client", mock_client):
        result = await get_chats()
        assert "Page out of range" in result # Since empty dialogs returned

@pytest.mark.asyncio
async def test_send_message(mock_client):
    from services.telegram_mcp.main import send_message
    
    with patch("services.telegram_mcp.main.client", mock_client):
        result = await send_message(chat_id=123, message="Hello")
        mock_client.send_message.assert_called()
        assert "Message sent successfully" in result
