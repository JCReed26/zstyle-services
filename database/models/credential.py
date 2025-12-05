"""
Credential Model

Stores sensitive authentication tokens and secrets for users.

GOVERNANCE: STRICT RULE - This table must NEVER be indexed by RAG.
            Secrets must be isolated from the memory/knowledge system.
            
Use this for:
    - OAuth tokens (Google, Telegram, etc.)
    - API keys for external services
    - Encrypted sensitive user data

DO NOT use UserMemory for any of this data.
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from database.engine import Base


def generate_uuid():
    return str(uuid.uuid4())


class CredentialType(str):
    """
    Known credential types.
    Use these constants for consistency.
    """
    GOOGLE_OAUTH = "google_oauth"
    TELEGRAM_SESSION = "telegram_session"
    TICKTICK_TOKEN = "ticktick_token"
    CUSTOM = "custom"


class Credential(Base):
    """
    Secure storage for user credentials and tokens.
    
    SECURITY NOTES:
    1. token_value should be encrypted at rest in production
    2. Never log token_value contents
    3. Never include in RAG indexing
    4. Implement token refresh logic in services layer
    """
    __tablename__ = "credentials"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # What kind of credential (google_oauth, telegram_session, etc.)
    credential_type = Column(String, nullable=False, index=True)
    
    # The actual token/secret (should be encrypted in production)
    token_value = Column(Text, nullable=False)
    
    # Optional refresh token for OAuth flows
    refresh_token = Column(Text, nullable=True)
    
    # When the token expires (NULL = never expires)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional credential data (scopes, etc.)
    extra_data = Column(JSON, default=dict)
    
    # Is this credential currently valid/active?
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship
    # user = relationship("User", back_populates="credentials")

    def __repr__(self):
        return f"<Credential(user_id={self.user_id}, type={self.credential_type}, active={self.is_active})>"

    def is_expired(self) -> bool:
        """Check if this credential has expired."""
        if self.expires_at is None:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) > self.expires_at
