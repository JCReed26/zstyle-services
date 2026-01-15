"""
Unit tests for Telegram webhook endpoint.

Following TDD principles - these tests are written before implementation.
Tests mock TelegramChannel and verify webhook endpoint behavior.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Mock core.config.settings before any imports
import unittest.mock
_mock_settings = unittest.mock.MagicMock()
_mock_settings.TELEGRAM_WEBHOOK_SECRET = None
_mock_settings.TELEGRAM_BOT_TOKEN = "test_token"
_mock_settings.SECRET_KEY = "test_secret_key_that_is_long_enough_for_validation"
_mock_settings.GOOGLE_API_KEY = "test_key"

# Create a mock module for core.config
_mock_config_module = unittest.mock.MagicMock()
_mock_config_module.settings = _mock_settings
sys.modules['core.config'] = _mock_config_module

# Don't mock telegram module - let python-telegram-bot handle it
# The MockUpdate class will be used in the fixture to patch Update.de_json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Mock Update class since there's a package conflict with telegram package
class MockUpdate:
    """Mock Update class for testing."""
    def __init__(self, update_id, message=None):
        self.update_id = update_id
        self.message = message
        self.effective_message = message
        self.effective_user = message.from_ if message else None
        self.effective_chat = message.chat if message else None
    
    @classmethod
    def de_json(cls, data, bot=None):
        """Mock de_json method."""
        return cls(data.get("update_id"), MockMessage.from_dict(data.get("message")) if data.get("message") else None)


class MockMessage:
    """Mock Message class for testing."""
    def __init__(self, message_id, text=None, from_user=None, chat=None, entities=None):
        self.message_id = message_id
        self.text = text
        self.from_ = from_user
        self.chat = chat
        self.entities = entities or []
    
    @classmethod
    def from_dict(cls, data):
        """Create MockMessage from dict."""
        if not data:
            return None
        return cls(
            message_id=data.get("message_id"),
            text=data.get("text"),
            from_user=MockUser.from_dict(data.get("from")) if data.get("from") else None,
            chat=MockChat.from_dict(data.get("chat")) if data.get("chat") else None,
            entities=[MockEntity.from_dict(e) for e in data.get("entities", [])]
        )


class MockUser:
    """Mock User class for testing."""
    def __init__(self, user_id, username=None, first_name=None):
        self.id = user_id
        self.username = username
        self.first_name = first_name
    
    @classmethod
    def from_dict(cls, data):
        """Create MockUser from dict."""
        if not data:
            return None
        return cls(
            user_id=data.get("id"),
            username=data.get("username"),
            first_name=data.get("first_name")
        )


class MockChat:
    """Mock Chat class for testing."""
    def __init__(self, chat_id, chat_type="private"):
        self.id = chat_id
        self.type = chat_type
    
    @classmethod
    def from_dict(cls, data):
        """Create MockChat from dict."""
        if not data:
            return None
        return cls(
            chat_id=data.get("id"),
            chat_type=data.get("type", "private")
        )


class MockEntity:
    """Mock Entity class for testing."""
    def __init__(self, entity_type, offset, length):
        self.type = entity_type
        self.offset = offset
        self.length = length
    
    @classmethod
    def from_dict(cls, data):
        """Create MockEntity from dict."""
        if not data:
            return None
        return cls(
            entity_type=data.get("type"),
            offset=data.get("offset"),
            length=data.get("length")
        )


# Patch Update class before importing modules
@pytest.fixture(autouse=True)
def mock_update_class():
    """Patch Update class before importing modules."""
    # Mock Update class - import modules after mocking
    import interface.telegram_webhook
    import channels.telegram_bot.channel
    
    interface.telegram_webhook.Update = MockUpdate
    channels.telegram_bot.channel.Update = MockUpdate
    
    yield MockUpdate


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_telegram_channel():
    """Create a mocked TelegramChannel instance."""
    channel = MagicMock()
    channel.process_webhook_update = AsyncMock()
    channel.application = MagicMock()
    channel.application.bot = MagicMock()
    return channel


@pytest.fixture
def app_with_webhook(mock_telegram_channel):
    """Create a FastAPI app with webhook router."""
    from interface.telegram_webhook import router, set_telegram_channel
    
    app = FastAPI()
    app.include_router(router)
    
    # Set the telegram channel for testing
    set_telegram_channel(mock_telegram_channel)
    
    return app


@pytest.fixture
def client(app_with_webhook):
    """Create a test client for the webhook endpoint."""
    return TestClient(app_with_webhook)


@pytest.fixture
def sample_update_json():
    """Sample Telegram update JSON."""
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 12345,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 12345,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1609459200,
            "text": "Hello, bot!"
        }
    }


@pytest.fixture
def sample_command_update_json():
    """Sample Telegram command update JSON."""
    return {
        "update_id": 123456790,
        "message": {
            "message_id": 2,
            "from": {
                "id": 12345,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 12345,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1609459200,
            "text": "/start",
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    }


# ============================================================================
# WEBHOOK ENDPOINT TESTS
# ============================================================================

def test_webhook_endpoint_success(client, mock_telegram_channel, sample_update_json):
    """Test that valid webhook request returns 200."""
    # Settings are already mocked globally
    response = client.post(
        "/webhook/telegram",
        json=sample_update_json
    )
    
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_endpoint_invalid_secret(client, mock_telegram_channel, sample_update_json):
    """Test that invalid secret token returns 401."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "correct_secret"
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
        )
        
        assert response.status_code == 401
        assert "Invalid secret token" in response.json()["detail"]
        mock_telegram_channel.process_webhook_update.assert_not_called()


def test_webhook_endpoint_missing_secret(client, mock_telegram_channel, sample_update_json):
    """Test that missing secret when required returns 401."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "required_secret"
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json
            # No header provided
        )
        
        assert response.status_code == 401
        assert "Invalid secret token" in response.json()["detail"]
        mock_telegram_channel.process_webhook_update.assert_not_called()


def test_webhook_endpoint_valid_secret(client, mock_telegram_channel, sample_update_json):
    """Test that valid secret token allows request through."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "correct_secret"
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json,
            headers={"X-Telegram-Bot-Api-Secret-Token": "correct_secret"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_endpoint_no_secret_required(client, mock_telegram_channel, sample_update_json):
    """Test that webhook works when TELEGRAM_WEBHOOK_SECRET is not set."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_invalid_json(client, mock_telegram_channel):
    """Test that invalid JSON returns 400."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        response = client.post(
            "/webhook/telegram",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        # FastAPI returns 400 for invalid JSON (caught by our error handler)
        assert response.status_code == 400
        mock_telegram_channel.process_webhook_update.assert_not_called()


def test_webhook_malformed_update(client, mock_telegram_channel):
    """Test that malformed update is handled gracefully."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        # Malformed update (missing required fields)
        malformed_update = {
            "update_id": 123
            # Missing message, callback_query, etc.
        }
        
        # Update.de_json should still work, but process_webhook_update might handle it
        response = client.post(
            "/webhook/telegram",
            json=malformed_update
        )
        
        # Should return 200 (webhook accepts it) but processing might fail internally
        # The endpoint should accept any valid Update JSON structure
        assert response.status_code == 200
        mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_processes_text_message(client, mock_telegram_channel, sample_update_json):
    """Test that text message updates are processed correctly."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json
        )
        
        assert response.status_code == 200
        
        # Verify that process_webhook_update was called with an Update object
        call_args = mock_telegram_channel.process_webhook_update.call_args
        assert call_args is not None
        update_arg = call_args[0][0]  # First positional argument
        assert update_arg is not None


def test_webhook_processes_command(client, mock_telegram_channel, sample_command_update_json):
    """Test that command messages are handled."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        response = client.post(
            "/webhook/telegram",
            json=sample_command_update_json
        )
        
        assert response.status_code == 200
        mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_processing_error(client, mock_telegram_channel, sample_update_json):
    """Test that processing errors are handled gracefully."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        # Make process_webhook_update raise an exception
        mock_telegram_channel.process_webhook_update.side_effect = Exception("Processing error")
        
        response = client.post(
            "/webhook/telegram",
            json=sample_update_json
        )
        
        # Should return 500 or handle error gracefully
        assert response.status_code in [500, 200]  # Depends on error handling strategy
        mock_telegram_channel.process_webhook_update.assert_called_once()


def test_webhook_empty_body(client, mock_telegram_channel):
    """Test that empty request body returns appropriate error."""
    with patch('interface.telegram_webhook.settings') as mock_settings:
        mock_settings.TELEGRAM_WEBHOOK_SECRET = None
        
        response = client.post(
            "/webhook/telegram",
            json={}
        )
        
        # Empty JSON should still be accepted (might be a valid empty update)
        # Or return 400/422 depending on validation
        assert response.status_code in [200, 400, 422]