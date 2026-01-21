"""
ZStyle Database Models

All database models consolidated in one file for simplicity.
Models are registered with SQLAlchemy's metadata for table creation.

Usage:
    from database.models import User, ActivityLog, Credential, OAuthState, ActivityLogSource, CredentialType
"""
from enum import Enum
from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Integer, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from datetime import datetime, timezone

from database.engine import Base


# =============================================================================
# ENUMS
# =============================================================================

class ActivityLogSource(str, Enum):
    """
    Source types for activity log entries.
    
    COPY-PASTE TEMPLATE for adding a new source:
    ============================================
    NEW_SOURCE = "new_source"  # Description
    """
    TELEGRAM = "telegram"       # User interaction via Telegram bot
    DISCORD = "discord"         # User interaction via Discord (future)
    API = "api"                 # Direct API/CLI interaction
    WEBHOOK = "webhook"         # External webhook trigger (Gmail, Calendar, etc.)
    CRON = "cron"               # Scheduled automation task
    SYSTEM = "system"           # Internal system events


class CredentialType(str):
    """
    Known credential types.
    Use these constants for consistency.
    """
    GOOGLE_OAUTH = "google_oauth"
    TELEGRAM_SESSION = "telegram_session"
    TICKTICK_TOKEN = "ticktick_token"
    CUSTOM = "custom"


# =============================================================================
# MODELS
# =============================================================================

class User(Base):
    """
    Core user profile entity for ZStyle.
    
    Uses UUID as primary key. Phone numbers can be stored in other_ids JSONB field.
    
    Each user can have multiple channel identities (Telegram ID, Discord ID, etc.)
    stored in telegram_id and other_ids JSONB field.
    
    GOVERNANCE: This table may be indexed by RAG for user context.
    """
    __tablename__ = "users"

    # Primary key (UUID generated locally)
    id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Channel-specific identifiers
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    
    # User display info
    username = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    
    # Future channel IDs (discord, etc.) stored as JSONB
    other_ids = Column(JSONB, default={}, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, telegram_id={self.telegram_id})>"


class Credential(Base):
    """
    Secure storage for user credentials and tokens.
    
    SECURITY NOTES:
    1. token_value should be encrypted at rest in production
    2. Never log token_value contents
    3. Never include in RAG indexing
    4. Implement token refresh logic in services layer
    
    GOVERNANCE: STRICT RULE - This table must NEVER be indexed by RAG.
                Secrets must be isolated from the memory/knowledge system.
    """
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # What kind of credential (google_oauth, ticktick_token, etc.)
    credential_type = Column(Text, nullable=False, index=True)
    
    # The actual token/secret (should be encrypted in production)
    token_value = Column(Text, nullable=False)
    
    # Optional refresh token for OAuth flows
    refresh_token = Column(Text, nullable=True)
    
    # When the token expires (NULL = never expires)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional credential data (scopes, etc.)
    extra_data = Column(JSONB, default={}, nullable=False)
    
    # Is this credential currently valid/active?
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Credential(user_id={self.user_id}, type={self.credential_type}, active={self.is_active})>"

    def is_expired(self) -> bool:
        """Check if this credential has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class ActivityLog(Base):
    """
    Timestamped log entry for user activity tracking.
    
    Every significant action in the system should create a log entry:
    - User messages (via any channel)
    - Automated actions (cron jobs, webhooks)
    - Agent tool executions
    - System events affecting the user
    
    GOVERNANCE: This table should NOT be indexed by RAG (it's operational data, not knowledge).
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # When this happened
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # What triggered this (use ActivityLogSource enum values)
    source = Column(Text, nullable=False, index=True)
    
    # Human-readable description of what happened
    action = Column(Text, nullable=False)
    
    # Optional structured data for filtering/analysis
    extra_data = Column(JSONB, default={}, nullable=False)

    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, source={self.source}, action={self.action[:30]}...)>"

    def format(self) -> str:
        """
        Format log entry as: HH:MM:SS-YYYY-MM-DD - source - action
        """
        ts = self.timestamp.strftime("%H:%M:%S-%Y-%m-%d")
        return f"{ts} - {self.source} - {self.action}"


class OAuthState(Base):
    """
    OAuth state token storage for CSRF protection.
    
    SECURITY NOTES:
    1. State tokens are single-use (deleted after consumption)
    2. States expire after 10 minutes
    3. States are cryptographically random (secrets.token_urlsafe)
    4. States link user_id to OAuth flow for proper credential storage
    """
    __tablename__ = "oauth_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    state_token = Column(Text, nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service = Column(Text, nullable=False)  # "google", "ticktick", etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)  # Track if state was used
    
    # Composite index for efficient lookups
    __table_args__ = (
        Index('idx_state_token_expires', 'state_token', 'expires_at'),
    )
    
    def is_expired(self) -> bool:
        """Check if state has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def __repr__(self):
        return f"<OAuthState(state_token={self.state_token[:8]}..., user_id={self.user_id}, service={self.service})>"


# Export all models and enums
__all__ = [
    # Models
    "User",
    "ActivityLog",
    "Credential",
    "OAuthState",
    # Enums/Types
    "ActivityLogSource",
    "CredentialType",
]
