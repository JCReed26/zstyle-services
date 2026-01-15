"""
ZStyle Database Package

Provides database engine, session management, and models.

Quick Start:
    from core.database import engine, AsyncSessionLocal, Base, get_db_session
    from core.database.models import User, ActivityLog, Credential
    from core.database.repositories import UserRepository
    
To reset the database (drops all tables and recreates):
    python reset_db.py
"""
from .engine import engine, AsyncSessionLocal, Base, get_db_session
from . import models
from . import repositories

__all__ = [
    "engine", 
    "AsyncSessionLocal", 
    "Base", 
    "get_db_session", 
    "models",
    "repositories"
]
