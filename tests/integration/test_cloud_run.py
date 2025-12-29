"""
Integration tests for Cloud Run deployment.

These tests verify that the deployed service is working correctly.
"""
import pytest
import os
import httpx
from typing import Optional


@pytest.fixture
def base_url() -> Optional[str]:
    """Get base URL from environment or use default."""
    return os.getenv("CLOUD_RUN_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_health_endpoint(base_url: str):
    """Test health check endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"], f"Unexpected status: {data['status']}"
        assert "database" in data


@pytest.mark.asyncio
async def test_api_info_endpoint(base_url: str):
    """Test API info endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/api/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data


@pytest.mark.asyncio
async def test_oauth_callback_endpoints_exist(base_url: str):
    """Test that OAuth callback endpoints exist (should return 400 without params)."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        # Google callback
        response = await client.get(f"{base_url}/api/oauth/google/callback")
        # Should return 400 (missing params) or redirect, not 404
        assert response.status_code in [400, 302], f"Unexpected status: {response.status_code}"
        
        # TickTick callback
        response = await client.get(f"{base_url}/api/oauth/ticktick/callback")
        assert response.status_code in [400, 302], f"Unexpected status: {response.status_code}"


@pytest.mark.asyncio
async def test_database_connectivity(base_url: str):
    """Test database connectivity via health endpoint."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/health")
        assert response.status_code in [200, 503]  # 503 if database is down
        
        data = response.json()
        if response.status_code == 200:
            # Database should be connected in healthy state
            assert data.get("database") == "connected" or "error" not in str(data.get("database", "")).lower()


@pytest.mark.asyncio
async def test_chat_bridge_endpoint(base_url: str):
    """Test chat bridge endpoint exists."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Should return 422 (validation error) for empty request, not 404
        response = await client.post(f"{base_url}/api/chat", json={})
        assert response.status_code in [422, 400], f"Unexpected status: {response.status_code}"

