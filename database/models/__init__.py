"""
ZStyle Database Models

All models are imported here for easy access and to ensure they're registered
with SQLAlchemy's metadata for table creation.

Usage:
    from database.models import User, UserMemory, ActivityLog, Credential
    
    # Or import specific enums
    from database.models.memory import MemorySlot
    from database.models.activity_log import ActivityLogSource
"""
from .user import User
from .memory import UserMemory, MemorySlot
from .activity_log import ActivityLog, ActivityLogSource
from .credential import Credential, CredentialType

__all__ = [
    # Models
    "User",
    "UserMemory", 
    "ActivityLog",
    "Credential",
    # Enums/Types
    "MemorySlot",
    "ActivityLogSource",
    "CredentialType",
]
