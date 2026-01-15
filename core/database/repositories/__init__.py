"""
Database Repositories

Repository pattern for database operations. Provides abstraction layer
for data access and business logic separation.

Usage:
    from core.database.repositories import UserRepository, CredentialRepository
    from core.database.engine import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(12345)
"""
from .user_repository import UserRepository
from .credential_repository import CredentialRepository

__all__ = ["UserRepository", "CredentialRepository"]
