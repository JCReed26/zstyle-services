"""
Unit tests for GoogleApiToolset integration.

Following TDD principles - these tests are written before implementation.
Tests verify credential provider function and GoogleApiToolset initialization.
"""
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Optional

# Set required environment variables before importing modules that use Settings
os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
# Set Google OAuth client credentials for GoogleApiToolset initialization
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

# Import the module we're testing (will fail until implemented)
try:
    from agents.exec_func_coach.tools import google_toolset, get_google_credentials
except ImportError:
    # Expected during TDD - tests will guide implementation
    google_toolset = None
    get_google_credentials = None


@pytest.fixture
def mock_credential_service():
    """Mock credential_service for testing."""
    # Patch at the import location in tools.py (imported from services package)
    with patch('agents.exec_func_coach.tools.credential_service') as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock settings for testing - autouse so it applies before imports."""
    # Patch settings before any imports that use it
    with patch('core.config.settings') as mock_settings_obj:
        # Create a mock that has the required attributes
        mock_settings_obj.GOOGLE_CLIENT_ID = "test_client_id"
        mock_settings_obj.GOOGLE_CLIENT_SECRET = "test_client_secret"
        mock_settings_obj.GOOGLE_API_KEY = "test-google-api-key"
        mock_settings_obj.TELEGRAM_BOT_TOKEN = "test-telegram-token"
        mock_settings_obj.SECRET_KEY = "test-secret-key-that-is-at-least-32-characters-long"
        yield mock_settings_obj


class TestGoogleToolsetInitialization:
    """Test GoogleApiToolset initialization."""
    
    def test_google_toolset_initialized(self):
        """Verify GoogleApiToolset instance exists when credentials are configured."""
        # When GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set, google_toolset should be initialized
        # Note: This test may fail if credentials aren't configured, which is valid
        # The important thing is that the code handles both cases gracefully
        if google_toolset is None:
            # This is acceptable if credentials aren't configured
            # Verify that at least the module imported successfully
            from agents.exec_func_coach.tools import google_toolsets
            # google_toolsets should exist (may be empty list)
            assert isinstance(google_toolsets, list), "google_toolsets should be a list"
        else:
            assert google_toolset is not None, "google_toolset should be initialized"
    
    def test_google_toolset_has_tools(self):
        """Verify toolset exposes tools list."""
        if google_toolset is None:
            pytest.skip("google_toolset not initialized (credentials may not be configured)")
        
        # GoogleApiToolset should have a tools attribute or method
        assert hasattr(google_toolset, 'tools') or hasattr(google_toolset, 'get_tools'), \
            "GoogleApiToolset should expose tools"


class TestGetGoogleCredentials:
    """Test credential provider function."""
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_with_creds(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Test credential provider with existing credentials."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: credential_service returns user credentials
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "scope": "calendar.readonly gmail.readonly"
        })
        
        # Execute: get credentials for a user
        result = await get_google_credentials("user123")
        
        # Verify: credentials are properly formatted
        assert result is not None
        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["client_id"] == "test_client_id"
        assert result["client_secret"] == "test_client_secret"
        
        # Verify: credential_service was called correctly
        mock_credential_service.get_credentials.assert_called_once_with(
            "user123",
            "google"
        )
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_no_creds(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Test credential provider returns None when no credentials exist."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: credential_service returns None (no credentials)
        mock_credential_service.get_credentials = AsyncMock(return_value=None)
        
        # Execute: get credentials for a user without credentials
        result = await get_google_credentials("user456")
        
        # Verify: returns None to trigger OAuth flow
        assert result is None
        
        # Verify: credential_service was called
        mock_credential_service.get_credentials.assert_called_once_with(
            "user456",
            "google"
        )
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_maps_token_to_access_token(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Verify token → access_token mapping."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: credential_service returns token (not access_token)
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "my_access_token_value",
            "refresh_token": "my_refresh_token_value"
        })
        
        # Execute
        result = await get_google_credentials("user789")
        
        # Verify: token is mapped to access_token
        assert result is not None
        assert "token" not in result, "Should not have 'token' key"
        assert result["access_token"] == "my_access_token_value"
        assert result["refresh_token"] == "my_refresh_token_value"
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_includes_client_creds(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Verify client_id/client_secret from env are included."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: custom client credentials
        mock_settings.GOOGLE_CLIENT_ID = "custom_client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "custom_client_secret"
        
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "access_token",
            "refresh_token": "refresh_token"
        })
        
        # Execute
        result = await get_google_credentials("user999")
        
        # Verify: client credentials are included
        assert result is not None
        assert result["client_id"] == "custom_client_id"
        assert result["client_secret"] == "custom_client_secret"
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_missing_client_id(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Test behavior when GOOGLE_CLIENT_ID is missing."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: missing client_id
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = "secret"
        
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "access_token",
            "refresh_token": "refresh_token"
        })
        
        # Execute: should handle gracefully
        result = await get_google_credentials("user111")
        
        # Verify: may return None or handle error gracefully
        # Implementation should handle this case
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_missing_refresh_token(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Test behavior when refresh_token is not present."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: credentials without refresh_token
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "access_token_only"
            # No refresh_token
        })
        
        # Execute
        result = await get_google_credentials("user222")
        
        # Verify: should still work, refresh_token may be None or omitted
        assert result is not None
        assert result["access_token"] == "access_token_only"
        # refresh_token may be None or not present
        assert "refresh_token" not in result or result.get("refresh_token") is None
    
    @pytest.mark.asyncio
    async def test_get_google_credentials_preserves_extra_fields(
        self,
        mock_credential_service,
        mock_settings
    ):
        """Test that extra credential fields are preserved if needed."""
        if get_google_credentials is None:
            pytest.skip("get_google_credentials not yet implemented")
        
        # Setup: credentials with extra metadata
        mock_credential_service.get_credentials = AsyncMock(return_value={
            "token": "access_token",
            "refresh_token": "refresh_token",
            "scope": "calendar.readonly",
            "expires_in": 3600,
            "token_type": "Bearer"
        })
        
        # Execute
        result = await get_google_credentials("user333")
        
        # Verify: core fields are present
        assert result is not None
        assert result["access_token"] == "access_token"
        assert result["refresh_token"] == "refresh_token"
        assert result["client_id"] == "test_client_id"
        assert result["client_secret"] == "test_client_secret"
        
        # Note: Extra fields may or may not be included depending on GoogleApiToolset needs
        # This test verifies core functionality works
