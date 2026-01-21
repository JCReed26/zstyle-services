#!/usr/bin/env python3
"""
Test Database Connection Script

Tests the PostgreSQL connection using the DATABASE_URL environment variable.
Run this from inside the Docker container to diagnose connection issues.
"""
import asyncio
import os
import sys
from urllib.parse import urlparse

async def test_connection():
    """Test database connection with detailed error reporting."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    print(f"📋 Connection String: {database_url[:50]}...")
    
    # Parse connection string
    try:
        parsed = urlparse(database_url.replace("postgresql+asyncpg://", "postgresql://"))
        print(f"✅ Connection string format: Valid")
        print(f"   Hostname: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Database: {parsed.path[1:] if parsed.path else 'N/A'}")
        print(f"   Username: {parsed.username}")
    except Exception as e:
        print(f"❌ ERROR: Invalid connection string format: {e}")
        return False
    
    # Test DNS resolution
    import socket
    try:
        hostname = parsed.hostname
        print(f"\n🔍 Testing DNS resolution for {hostname}...")
        ip_address = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution successful: {hostname} -> {ip_address}")
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        print(f"   This is likely the root cause of your connection issue!")
        print(f"   Solutions:")
        print(f"   1. Ensure PostgreSQL container is running: docker compose ps db")
        print(f"   2. Check Docker DNS settings in docker-compose.yml")
        print(f"   3. Verify DATABASE_URL uses service name 'db' for local container")
        return False
    except Exception as e:
        print(f"⚠️  DNS resolution warning: {e}")
    
    # Test async connection
    try:
        print(f"\n🔌 Testing PostgreSQL connection...")
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Convert to async URL if needed
        async_url = database_url
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(
            async_url,
            pool_pre_ping=True,
            connect_args={"server_settings": {"application_name": "zstyle_test"}}
        )
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test, version() as pg_version"))
            row = result.fetchone()
            print(f"✅ Connection successful!")
            print(f"   Test query result: {row[0]}")
            print(f"   PostgreSQL version: {row[1][:50]}...")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Verify password is correct in .env file")
        print(f"   2. Check PostgreSQL container is running: docker compose ps db")
        print(f"   3. Ensure DATABASE_URL uses service name 'db' for local container")
        print(f"   4. Verify container health check passed")
        
        # Check for specific error types
        error_str = str(e).lower()
        if "name or service not known" in error_str:
            print(f"\n   💡 DNS Error Detected:")
            print(f"      - This means Docker cannot resolve the hostname")
            print(f"      - Solution: Use Docker service name 'db' in connection string")
            print(f"      - Current: {parsed.hostname}")
            print(f"      - Should be: db (for local container)")
        elif "connection refused" in error_str or "timeout" in error_str:
            print(f"\n   💡 Connection Refused/Timeout:")
            print(f"      - Check PostgreSQL container logs: docker compose logs db")
            print(f"      - Verify container health check: docker compose ps db")
        elif "password" in error_str or "authentication" in error_str:
            print(f"\n   💡 Authentication Error:")
            print(f"      - Verify POSTGRES_PASSWORD in .env file")
            print(f"      - Check if password needs URL encoding")
            print(f"      - Ensure DATABASE_URL matches .env credentials")
        
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ZStyle Database Connection Test")
    print("=" * 60)
    print()
    
    success = asyncio.run(test_connection())
    
    print()
    print("=" * 60)
    if success:
        print("✅ All tests passed! Database connection is working.")
        sys.exit(0)
    else:
        print("❌ Connection test failed. See errors above.")
        sys.exit(1)
