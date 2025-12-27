"""
User Memory Model

This is the core of ZStyle's Memory-First Architecture. Instead of storing
chat history (which bloats context), we store structured "memory slots" that
agents know how to read and write.

MEMORY TYPES:
1. Standardized Slots (MemorySlot enum) - Well-known locations all agents understand
2. Flexible Memories - Agent-specific or ad-hoc memories with tags for retrieval

GOVERNANCE: This table IS indexed by RAG for user context retrieval.
            NEVER store secrets here - use Credential model instead.

Example Memory Entries:
    - slot="current_goal", value={"goal": "Launch MVP", "deadline": "2025-01-15"}
    - slot=None, key="exec_func_coach.habit_tracking", value={"morning_routine": [...]}
"""
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from database.core import Base


def generate_uuid():
    return str(uuid.uuid4())


class MemorySlot(str, Enum):
    """
    Standardized memory locations that ALL agents understand.
    
    When adding a new slot:
    1. Add it here
    2. Document what data structure it expects in the docstring
    3. Update agent instructions to reference the new slot
    
    COPY-PASTE TEMPLATE for adding a new slot:
    =========================================
    NEW_SLOT_NAME = "new_slot_name"  # Description of what this stores
    """
    # Core goal tracking
    CURRENT_GOAL = "current_goal"           # {"goal": str, "deadline": str, "priority": int}
    GOAL_PROGRESS = "goal_progress"         # {"milestones": [...], "percent_complete": int}
    
    # User preferences (affects agent behavior)
    USER_PREFERENCES = "user_preferences"   # {"timezone": str, "temp_unit": "C"|"F", ...}
    COMMUNICATION_STYLE = "comm_style"      # {"verbosity": "brief"|"detailed", "tone": str}
    
    # Task management
    ACTIVE_TASKS = "active_tasks"           # [{"task": str, "due": str, "priority": int}, ...]
    
    # Personal context
    DAILY_SCHEDULE = "daily_schedule"       # {"wake_time": str, "work_hours": {...}}
    IMPORTANT_DATES = "important_dates"     # [{"date": str, "event": str, "recurring": bool}]


class UserMemory(Base):
    """
    Persistent memory storage for users.
    
    Two usage patterns:
    1. Standardized slots: slot is set, key matches slot value
       - Used for well-known data all agents need
       - Example: slot="current_goal", key="current_goal"
    
    2. Flexible memories: slot is NULL, key is agent-specific
       - Used for agent-specific or ad-hoc data
       - Example: slot=None, key="exec_func_coach.habit_streak"
       - Use tags for retrieval: tags=["habits", "tracking"]
    """
    __tablename__ = "user_memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Memory identification
    slot = Column(String, nullable=True, index=True)  # NULL = flexible memory
    key = Column(String, nullable=False)               # Unique per user+slot combo
    
    # The actual memory data (JSON blob)
    value = Column(JSON, nullable=False)
    
    # For flexible memory retrieval
    tags = Column(JSON, default=list)  # ["habits", "goals", "exec_func_coach"]
    
    # Optional description for clarity
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship
    # user = relationship("User", back_populates="memories")

    def __repr__(self):
        return f"<UserMemory(user_id={self.user_id}, slot={self.slot}, key={self.key})>"
