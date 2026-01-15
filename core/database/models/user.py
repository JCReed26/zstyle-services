"""
User Model

Stores core user identity information. Links external channel IDs (Telegram, Discord)
to internal ZStyle user IDs.

GOVERNANCE: This table may be indexed by RAG for user context.
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from core.database.engine import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    """
    Core user entity for ZStyle.
    
    Each user can have multiple channel identities (Telegram ID, Discord ID, etc.)
    but they all map to a single internal user_id.
    """
    __tablename__ = "users"

    # Internal unique identifier
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Channel-specific identifiers
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    discord_id = Column(BigInteger, unique=True, nullable=True, index=True)
    
    # User display info
    username = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships (defined in other models)
    # memories = relationship("UserMemory", back_populates="user")
    # activity_logs = relationship("ActivityLog", back_populates="user")
    # credentials = relationship("Credential", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
