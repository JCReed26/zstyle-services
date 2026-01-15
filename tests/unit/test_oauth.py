"""
Unit tests for OAuth endpoints.

Following TDD principles - these tests are written before implementation.
Tests use TestClient for integration-style testing and mock external OAuth providers.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from typing import Dict, Any

# Set required environment variables before importing modules
os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("TICKTICK_CLIENT_ID", "test-ticktick-client-id")
os.environ.setdefault("TICKTICK_CLIENT_SECRET", "test-ticktick-client-secret")

# Import app - will fail until routers are implemented
try:
    from main import app
except ImportError:
    app = None


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """Create a TestClient instance."""
    if app is None:
        pytest.skip("App not yet implemented")
    return TestClient(app)


@pytest.fixture
def mock_credential_service():
    """Mock credential_service for testing."""
    with patch('interface.oauth.google.credential_service') as mock, \
         patch('interface.oauth.ticktick.credential_service') as mock2:
        # Both modules use credential_service, so patch both
        mock.store_credentials = AsyncMock()
        mock2.store_credentials = AsyncMock()
        yield mock


@pytest.fixture
def mock_google_oauth_flow():
    """Mock Google OAuth flow."""
    with patch('interface.oauth.google.Flow') as mock_flow_class:
        mock_credentials = MagicMock()
        mock_credentials.token = "test_access_token"
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.expiry = None  # No expiry
        mock_credentials.scopes = ["https://www.googleapis.com/auth/calendar"]
        
        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow_instance.fetch_token = MagicMock(return_value=None)
        mock_flow_class.from_client_config.return_value = mock_flow_instance
        
        yield mock_flow_class


@pytest.fixture
def mock_ticktick_oauth():
    """Mock TickTick OAuth2 client."""
    with patch('interface.oauth.ticktick.OAuth2') as mock_oauth_class:
        mock_oauth_instance = MagicMock()
        # Mock get_authorization_url to return URL without state (our code will append it)
        # Or accept state parameter if provided
        def mock_get_auth_url(state=None):
            base_url = "https://ticktick.com/oauth/authorize"
            if state:
                return f"{base_url}?state={state}"
            return base_url
        
        mock_oauth_instance.get_authorization_url = MagicMock(side_effect=mock_get_auth_url)
        mock_oauth_instance.get_access_token.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600
        }
        mock_oauth_class.return_value = mock_oauth_instance
        yield mock_oauth_instance


# ============================================================================
# GOOGLE OAUTH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_google_oauth_initiate_success(test_client, mock_credential_service):
    """Test successful Google OAuth initiation returns URL and state."""
    response = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "state" in data
    assert isinstance(data["state"], str)
    assert len(data["state"]) > 0
    assert "accounts.google.com" in data["url"] or "google.com" in data["url"]
    assert data["state"] in data["url"]  # State should be in the URL


@pytest.mark.asyncio
async def test_google_oauth_initiate_missing_user_id(test_client):
    """Test that missing user_id returns 422."""
    response = test_client.get("/oauth/google/initiate")
    
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_google_oauth_initiate_missing_config(test_client, mock_credential_service):
    """Test that missing client credentials returns 500."""
    with patch('interface.oauth.google.settings') as mock_settings:
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = None
        
        response = test_client.get("/oauth/google/initiate?user_id=test_user_123")
        
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_google_oauth_callback_success(test_client, mock_credential_service, mock_google_oauth_flow):
    """Test successful Google OAuth callback exchanges code and stores credentials."""
    # First, initiate to get a state
    initiate_response = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    # Mock the token exchange
    with patch('interface.oauth.google.Flow') as mock_flow_class:
        mock_flow_instance = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.token = "test_access_token"
        mock_credentials.refresh_token = "test_refresh_token"
        mock_credentials.expiry = None
        mock_credentials.scopes = ["https://www.googleapis.com/auth/calendar"]
        mock_flow_instance.credentials = mock_credentials
        mock_flow_instance.fetch_token = MagicMock(return_value=None)
        
        # Mock the flow creation and token fetch
        mock_flow_class.from_client_config.return_value = mock_flow_instance
        
        # Callback
        response = test_client.get(f"/oauth/google/callback?code=test_code&state={state}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_id"] == "test_user_123"
        
        # Verify credentials were stored
        mock_credential_service.store_credentials.assert_called_once()
        call_args = mock_credential_service.store_credentials.call_args
        assert call_args[1]["user_id"] == "test_user_123"
        assert call_args[1]["service"] == "google"
        stored_creds = call_args[1]["credentials"]
        assert "token" in stored_creds


@pytest.mark.asyncio
async def test_google_oauth_callback_invalid_state(test_client, mock_credential_service):
    """Test that invalid state returns 400."""
    response = test_client.get("/oauth/google/callback?code=test_code&state=invalid_state")
    
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_oauth_callback_missing_code(test_client, mock_credential_service):
    """Test that missing code returns 400."""
    # First, initiate to get a state
    initiate_response = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    response = test_client.get(f"/oauth/google/callback?state={state}")
    
    assert response.status_code == 422  # FastAPI validation error for missing query param


@pytest.mark.asyncio
async def test_google_oauth_callback_token_exchange_failure(test_client, mock_credential_service):
    """Test that token exchange failure is handled gracefully."""
    # First, initiate to get a state
    initiate_response = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    # Mock token exchange failure
    with patch('interface.oauth.google.Flow') as mock_flow_class:
        mock_flow_instance = MagicMock()
        mock_flow_instance.fetch_token = MagicMock(side_effect=Exception("Token exchange failed"))
        mock_flow_class.from_client_config.return_value = mock_flow_instance
        
        response = test_client.get(f"/oauth/google/callback?code=invalid_code&state={state}")
        
        assert response.status_code == 500
        assert "error" in response.json() or "failed" in response.json()["detail"].lower()


# ============================================================================
# TICKTICK OAUTH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_ticktick_oauth_initiate_success(test_client, mock_credential_service, mock_ticktick_oauth):
    """Test successful TickTick OAuth initiation returns URL and state."""
    response = test_client.get("/oauth/ticktick/initiate?user_id=test_user_123")
    
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "state" in data
    assert isinstance(data["state"], str)
    assert len(data["state"]) > 0


@pytest.mark.asyncio
async def test_ticktick_oauth_initiate_missing_user_id(test_client):
    """Test that missing user_id returns 422."""
    response = test_client.get("/oauth/ticktick/initiate")
    
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.asyncio
async def test_ticktick_oauth_initiate_missing_config(test_client, mock_credential_service):
    """Test that missing client credentials returns 500."""
    with patch('interface.oauth.ticktick.settings') as mock_settings:
        mock_settings.TICKTICK_CLIENT_ID = None
        mock_settings.TICKTICK_CLIENT_SECRET = None
        
        response = test_client.get("/oauth/ticktick/initiate?user_id=test_user_123")
        
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_ticktick_oauth_callback_success(test_client, mock_credential_service, mock_ticktick_oauth):
    """Test successful TickTick OAuth callback exchanges code and stores credentials."""
    # First, initiate to get a state
    initiate_response = test_client.get("/oauth/ticktick/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    # Callback
    response = test_client.get(f"/oauth/ticktick/callback?code=test_code&state={state}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user_id"] == "test_user_123"
    
    # Verify credentials were stored
    mock_credential_service.store_credentials.assert_called_once()
    call_args = mock_credential_service.store_credentials.call_args
    assert call_args[1]["user_id"] == "test_user_123"
    assert call_args[1]["service"] == "ticktick"
    stored_creds = call_args[1]["credentials"]
    assert "token" in stored_creds


@pytest.mark.asyncio
async def test_ticktick_oauth_callback_invalid_state(test_client, mock_credential_service):
    """Test that invalid state returns 400."""
    response = test_client.get("/oauth/ticktick/callback?code=test_code&state=invalid_state")
    
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ticktick_oauth_callback_missing_code(test_client, mock_credential_service):
    """Test that missing code returns 400."""
    # First, initiate to get a state
    initiate_response = test_client.get("/oauth/ticktick/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    response = test_client.get(f"/oauth/ticktick/callback?state={state}")
    
    assert response.status_code == 422  # FastAPI validation error for missing query param


# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_oauth_state_is_unique(test_client, mock_credential_service):
    """Test that each initiation generates unique state."""
    response1 = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    response2 = test_client.get("/oauth/google/initiate?user_id=test_user_123")
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    state1 = response1.json()["state"]
    state2 = response2.json()["state"]
    
    assert state1 != state2  # States should be unique


@pytest.mark.asyncio
async def test_oauth_state_is_one_time_use(test_client, mock_credential_service, mock_ticktick_oauth):
    """Test that state is consumed after callback."""
    # Initiate
    initiate_response = test_client.get("/oauth/ticktick/initiate?user_id=test_user_123")
    assert initiate_response.status_code == 200
    state = initiate_response.json()["state"]
    
    # First callback should succeed
    callback_response1 = test_client.get(f"/oauth/ticktick/callback?code=test_code&state={state}")
    assert callback_response1.status_code == 200
    
    # Second callback with same state should fail
    callback_response2 = test_client.get(f"/oauth/ticktick/callback?code=test_code&state={state}")
    assert callback_response2.status_code == 400  # State already consumed
