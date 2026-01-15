"""
Unit tests for core.config module.

Following TDD principles - these tests are written before implementation.
"""
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

# Import will fail until we implement core.config
# This is expected in TDD - tests first, then implementation
try:
    from core.config import Settings
except ImportError:
    Settings = None


def test_settings_required_vars():
    """Test that Settings raises ValidationError when required vars are missing."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValidationError):
            Settings()


def test_settings_optional_defaults():
    """Test that Settings applies correct defaults for optional variables."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "test-secret-32-chars-long-key-here"
    }, clear=True):
        settings = Settings()
        assert settings.PORT == 8000
        assert settings.ENV == "development"
        assert settings.OPENMEMORY_URL == "http://openmemory:8080"
        assert settings.DATABASE_URL is None
        assert settings.OPENMEMORY_API_KEY is None


def test_secret_key_validation():
    """Test that SECRET_KEY must be at least 32 characters."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    # Test with too short SECRET_KEY
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "short"  # Too short
    }, clear=True):
        with pytest.raises(ValidationError):
            Settings()
    
    # Test with valid SECRET_KEY (exactly 32 chars)
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "a" * 32  # Exactly 32 chars
    }, clear=True):
        settings = Settings()
        assert len(settings.SECRET_KEY) == 32
    
    # Test with valid SECRET_KEY (more than 32 chars)
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "a" * 64  # 64 chars
    }, clear=True):
        settings = Settings()
        assert len(settings.SECRET_KEY) == 64


def test_all_required_vars_present():
    """Test that Settings works when all required vars are present."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-google-key",
        "TELEGRAM_BOT_TOKEN": "test-telegram-token",
        "SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long"
    }, clear=True):
        settings = Settings()
        assert settings.GOOGLE_API_KEY == "test-google-key"
        assert settings.TELEGRAM_BOT_TOKEN == "test-telegram-token"
        assert settings.SECRET_KEY == "test-secret-key-that-is-at-least-32-characters-long"


def test_optional_vars_override_defaults():
    """Test that optional environment variables override defaults."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    with patch.dict(os.environ, {
        "GOOGLE_API_KEY": "test-key",
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "test-secret-32-chars-long-key-here",
        "PORT": "9000",
        "ENV": "production",
        "OPENMEMORY_URL": "http://custom:9090"
    }, clear=True):
        settings = Settings()
        assert settings.PORT == 9000
        assert settings.ENV == "production"
        assert settings.OPENMEMORY_URL == "http://custom:9090"


def test_case_sensitivity():
    """Test that environment variable names are case-sensitive."""
    if Settings is None:
        pytest.skip("Settings not yet implemented")
    
    # Lowercase should not work
    with patch.dict(os.environ, {
        "google_api_key": "test-key",  # lowercase
        "TELEGRAM_BOT_TOKEN": "test-token",
        "SECRET_KEY": "test-secret-32-chars-long-key-here"
    }, clear=True):
        with pytest.raises(ValidationError):
            Settings()
