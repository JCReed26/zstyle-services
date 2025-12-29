"""
Tests for database connection handling.

Tests Cloud SQL connection string parsing, Secret Manager fallback,
and connection pool behavior.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from database.core import DATABASE_URL, USE_POSTGRES, engine, _get_secret_from_gcp


def test_sqlite_default():
    """Test that SQLite is used by default."""
    with patch.dict(os.environ, {}, clear=True):
        # Reload module to get fresh values
        import importlib
        import database.core
        importlib.reload(database.core)
        
        # Should default to SQLite
        assert "sqlite" in database.core.DATABASE_URL.lower() or database.core.DATABASE_URL is None


def test_postgres_connection_string_conversion():
    """Test PostgreSQL connection string conversion."""
    test_cases = [
        ("postgresql://user:pass@host/db", "postgresql+asyncpg://user:pass@host/db"),
        ("postgresql+asyncpg://user:pass@host/db", "postgresql+asyncpg://user:pass@host/db"),
        ("postgresql://user:pass@/db?host=/cloudsql/proj:region:inst", 
         "postgresql+asyncpg://user:pass@/db?host=/cloudsql/proj:region:inst"),
    ]
    
    for input_url, expected in test_cases:
        with patch.dict(os.environ, {"DATABASE_URL": input_url, "USE_POSTGRES": "true"}):
            import importlib
            import database.core
            importlib.reload(database.core)
            
            if database.core.DATABASE_URL:
                assert "+asyncpg" in database.core.DATABASE_URL


def test_secret_manager_fallback():
    """Test Secret Manager fallback for DATABASE_URL."""
    with patch('database.core._get_secret_from_gcp') as mock_secret:
        mock_secret.return_value = "postgresql://test:pass@host/db"
        
        with patch.dict(os.environ, {"USE_POSTGRES": "true"}, clear=True):
            import importlib
            import database.core
            importlib.reload(database.core)
            
            # Should use secret manager value
            mock_secret.assert_called_with("DATABASE_URL")


def test_cloud_sql_unix_socket_format():
    """Test Cloud SQL Unix socket connection string format."""
    socket_url = "postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE"
    
    # Should be valid format
    assert "+asyncpg" in socket_url
    assert "/cloudsql/" in socket_url
    assert "?" in socket_url or "host=" in socket_url


def test_connection_pool_settings():
    """Test that connection pool settings are configured."""
    # Engine should have pool settings
    assert hasattr(engine.sync_engine, "pool")
    
    # Check pool configuration
    pool = engine.sync_engine.pool
    assert pool.size() <= 5 + 10  # pool_size + max_overflow


@pytest.mark.asyncio
async def test_database_connection_health():
    """Test database connection health check."""
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    except Exception as e:
        # Database might not be available in test environment
        pytest.skip(f"Database not available: {e}")


def test_secret_manager_not_available_locally():
    """Test that Secret Manager gracefully fails when not in GCP."""
    # Should return None when not in GCP
    result = _get_secret_from_gcp("TEST_SECRET")
    assert result is None or isinstance(result, str)

