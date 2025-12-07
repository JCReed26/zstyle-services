#!/usr/bin/env python3
"""
Database Reset Script

Drops all tables and recreates them based on current model definitions.
Use this during development when you modify models.

Usage:
    python reset_db.py

WARNING: This will DELETE all data in the database!
"""
import asyncio
import sys

from database.engine import engine, Base

# Import all models to ensure they're registered with Base.metadata
# This is required for create_all() to know about all tables
from database.models import User, UserMemory, ActivityLog, Credential


async def reset_db():
    """Drop all tables and recreate them."""
    print("=" * 50)
    print("ZStyle Database Reset")
    print("=" * 50)
    
    async with engine.begin() as conn:
        print("\n[1/2] Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("      Done.")
        
        print("\n[2/2] Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("      Done.")
    
    # Clean up connection
    await engine.dispose()
    
    print("\n" + "=" * 50)
    print("Database reset complete!")
    print("Tables created:")
    for table in Base.metadata.tables:
        print(f"  - {table}")
    print("=" * 50)


if __name__ == "__main__":
    # Confirm if running interactively
    if sys.stdin.isatty():
        response = input("\nThis will DELETE all data. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    asyncio.run(reset_db())
