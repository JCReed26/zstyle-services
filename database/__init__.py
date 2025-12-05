"""
ZStyle Database Package

Provides database engine, session management, and models.

Quick Start:
    from database import engine, AsyncSessionLocal, Base, get_db_session
    from database.models import User, UserMemory, ActivityLog, Credential
    
To reset the database (drops all tables and recreates):
    python reset_db.py
"""
from .engine import engine, AsyncSessionLocal, Base, get_db_session
from . import models

__all__ = [
    "engine", 
    "AsyncSessionLocal", 
    "Base", 
    "get_db_session", 
    "models"
]
