"""
Activity Log Model

Per-user chronological log of ALL system interactions. This provides transparency
to users about what the system is doing on their behalf.

Log Format: HH:MM:SS-YYYY-MM-DD - source - action
Example entries:
    - 00:06:00-2025-01-01 - cron - handle inbox
    - 00:06:02-2025-01-01 - cron - schedule tasks on calendar
    - 00:06:10-2025-01-01 - webhook - gmail marketing email left read no action
    - 00:07:01-2025-01-01 - telegram - user inquired about day
    - 00:10:15-2025-01-01 - telegram - user inquired about data from second brain

USER ACCESS:
    - View last 25 logs via command
    - Export all logs to email attachment

GOVERNANCE: This table should NOT be indexed by RAG (it's operational data, not knowledge).
"""
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database.engine import Base


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


class ActivityLog(Base):
    """
    Timestamped log entry for user activity tracking.
    
    Every significant action in the system should create a log entry:
    - User messages (via any channel)
    - Automated actions (cron jobs, webhooks)
    - Agent tool executions
    - System events affecting the user
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # When this happened
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # What triggered this (use ActivityLogSource enum values)
    source = Column(String, nullable=False, index=True)
    
    # Human-readable description of what happened
    action = Column(Text, nullable=False)
    
    # Optional structured data for filtering/analysis
    extra_data = Column(JSON, default=dict)

    # Relationship
    # user = relationship("User", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, source={self.source}, action={self.action[:30]}...)>"

    def format(self) -> str:
        """
        Format log entry as: HH:MM:SS-YYYY-MM-DD - source - action
        """
        ts = self.timestamp.strftime("%H:%M:%S-%Y-%m-%d")
        return f"{ts} - {self.source} - {self.action}"
