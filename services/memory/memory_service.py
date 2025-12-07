"""
ZStyle Memory Service

Memory-First Architecture: Instead of storing chat history (which bloats context),
we store structured "memory slots" that agents know how to read/write.

This service provides:
1. Standardized Slots - Well-known memory locations all agents understand
2. Flexible Memories - Agent-specific or ad-hoc data with tags for retrieval
3. User Context - Aggregated view of user's memory for agent injection

USAGE EXAMPLE (in agent tools):
===============================
from services.memory import memory_service
from database.models import MemorySlot

# Get standardized slot
current_goal = await memory_service.get_memory_slot(
    user_id="user123", 
    slot=MemorySlot.CURRENT_GOAL
)

# Set standardized slot
await memory_service.set_memory_slot(
    user_id="user123",
    slot=MemorySlot.CURRENT_GOAL,
    value={"goal": "Launch MVP", "deadline": "2025-01-15"}
)

# Store flexible memory (agent-specific)
await memory_service.store_flexible_memory(
    user_id="user123",
    key="exec_func_coach.morning_routine",
    value={"steps": ["wake up", "exercise", "journal"]},
    tags=["habits", "routine"]
)

# Get user context for agent injection
context = await memory_service.get_user_context(user_id="user123")
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from database.engine import AsyncSessionLocal
from database.models import UserMemory, MemorySlot


def generate_uuid():
    return str(uuid.uuid4())


@dataclass
class UserContext:
    """
    Aggregated user context for agent injection.
    Contains all standardized slots plus relevant flexible memories.
    """
    user_id: str
    timezone: Optional[str] = None
    current_goal: Optional[Dict[str, Any]] = None
    goal_progress: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    communication_style: Optional[Dict[str, Any]] = None
    active_tasks: Optional[List[Dict[str, Any]]] = None
    flexible_memories: Optional[List[Dict[str, Any]]] = None

    def to_prompt_context(self) -> str:
        """
        Format context for injection into agent prompts.
        Only includes non-empty values.
        """
        parts = []
        
        if self.timezone:
            parts.append(f"Timezone: {self.timezone}")
        if self.current_goal:
            parts.append(f"Current Goal: {self.current_goal}")
        if self.goal_progress:
            parts.append(f"Goal Progress: {self.goal_progress}")
        if self.preferences:
            parts.append(f"User Preferences: {self.preferences}")
        if self.communication_style:
            parts.append(f"Communication Style: {self.communication_style}")
        if self.active_tasks:
            parts.append(f"Active Tasks: {self.active_tasks}")
        
        return "\n".join(parts) if parts else "No stored context available."


class ZStyleMemoryService:
    """
    Central memory service for the ZStyle system.
    
    Manages both standardized slots (well-known locations) and
    flexible memories (agent-specific data).
    """

    async def _get_session(self) -> AsyncSession:
        """Get a database session."""
        return AsyncSessionLocal()

    # =========================================================================
    # STANDARDIZED SLOT OPERATIONS
    # =========================================================================

    async def get_memory_slot(
        self,
        user_id: str,
        slot: MemorySlot
    ) -> Optional[Any]:
        """
        Get a standardized memory slot value.
        
        Args:
            user_id: The user's ID
            slot: The MemorySlot enum value
            
        Returns:
            The slot's value (JSON) or None if not set
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserMemory).where(
                    and_(
                        UserMemory.user_id == user_id,
                        UserMemory.slot == slot.value
                    )
                )
            )
            memory = result.scalar_one_or_none()
            return memory.value if memory else None

    async def set_memory_slot(
        self,
        user_id: str,
        slot: MemorySlot,
        value: Any,
        description: Optional[str] = None
    ) -> UserMemory:
        """
        Set a standardized memory slot value (upsert).
        
        Args:
            user_id: The user's ID
            slot: The MemorySlot enum value
            value: JSON-serializable value to store
            description: Optional human-readable description
            
        Returns:
            The created or updated UserMemory record
        """
        async with AsyncSessionLocal() as db:
            # Check if exists
            result = await db.execute(
                select(UserMemory).where(
                    and_(
                        UserMemory.user_id == user_id,
                        UserMemory.slot == slot.value
                    )
                )
            )
            memory = result.scalar_one_or_none()
            
            if memory:
                # Update existing
                memory.value = value
                if description:
                    memory.description = description
            else:
                # Create new
                memory = UserMemory(
                    id=generate_uuid(),
                    user_id=user_id,
                    slot=slot.value,
                    key=slot.value,  # For standardized slots, key matches slot
                    value=value,
                    description=description,
                    tags=[]
                )
                db.add(memory)
            
            await db.commit()
            await db.refresh(memory)
            return memory

    async def delete_memory_slot(
        self,
        user_id: str,
        slot: MemorySlot
    ) -> bool:
        """Delete a standardized memory slot."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(UserMemory).where(
                    and_(
                        UserMemory.user_id == user_id,
                        UserMemory.slot == slot.value
                    )
                )
            )
            memory = result.scalar_one_or_none()
            
            if memory:
                await db.delete(memory)
                await db.commit()
                return True
            return False

    # =========================================================================
    # FLEXIBLE MEMORY OPERATIONS
    # =========================================================================

    async def store_flexible_memory(
        self,
        user_id: str,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> UserMemory:
        """
        Store a flexible (agent-specific) memory.
        
        Flexible memories don't use standardized slots - they use a custom key
        and can be tagged for retrieval.
        
        Args:
            user_id: The user's ID
            key: Unique key (recommend: "agent_name.memory_name")
            value: JSON-serializable value
            tags: List of tags for filtering/retrieval
            description: Optional description
            
        Returns:
            The created or updated UserMemory record
        """
        async with AsyncSessionLocal() as db:
            # Check if exists (by key)
            result = await db.execute(
                select(UserMemory).where(
                    and_(
                        UserMemory.user_id == user_id,
                        UserMemory.key == key,
                        UserMemory.slot.is_(None)  # Flexible memories have no slot
                    )
                )
            )
            memory = result.scalar_one_or_none()
            
            if memory:
                memory.value = value
                if tags is not None:
                    memory.tags = tags
                if description:
                    memory.description = description
            else:
                memory = UserMemory(
                    id=generate_uuid(),
                    user_id=user_id,
                    slot=None,  # No slot = flexible memory
                    key=key,
                    value=value,
                    tags=tags or [],
                    description=description
                )
                db.add(memory)
            
            await db.commit()
            await db.refresh(memory)
            return memory

    async def get_flexible_memories(
        self,
        user_id: str,
        tags: Optional[List[str]] = None,
        key_prefix: Optional[str] = None
    ) -> List[UserMemory]:
        """
        Retrieve flexible memories by tags or key prefix.
        
        Args:
            user_id: The user's ID
            tags: Filter by any of these tags (OR logic)
            key_prefix: Filter by key prefix (e.g., "exec_func_coach.")
            
        Returns:
            List of matching UserMemory records
        """
        async with AsyncSessionLocal() as db:
            query = select(UserMemory).where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.slot.is_(None)  # Only flexible memories
                )
            )
            
            if key_prefix:
                query = query.where(UserMemory.key.startswith(key_prefix))
            
            result = await db.execute(query)
            memories = result.scalars().all()
            
            # Filter by tags in Python (JSON array querying is DB-specific)
            if tags:
                memories = [
                    m for m in memories 
                    if any(tag in (m.tags or []) for tag in tags)
                ]
            
            return memories

    # =========================================================================
    # USER CONTEXT AGGREGATION
    # =========================================================================

    async def get_user_context(
        self,
        user_id: str,
        include_flexible: bool = False,
        flexible_tags: Optional[List[str]] = None
    ) -> UserContext:
        """
        Get aggregated user context for agent injection.
        
        This builds a UserContext object containing all standardized slots
        plus optionally relevant flexible memories.
        
        Args:
            user_id: The user's ID
            include_flexible: Whether to include flexible memories
            flexible_tags: If including flexible, filter by these tags
            
        Returns:
            UserContext dataclass with all available context
        """
        context = UserContext(user_id=user_id)
        
        # Load standardized slots
        context.timezone = await self.get_memory_slot(user_id, MemorySlot.TIMEZONE)
        context.current_goal = await self.get_memory_slot(user_id, MemorySlot.CURRENT_GOAL)
        context.goal_progress = await self.get_memory_slot(user_id, MemorySlot.GOAL_PROGRESS)
        context.preferences = await self.get_memory_slot(user_id, MemorySlot.USER_PREFERENCES)
        context.communication_style = await self.get_memory_slot(user_id, MemorySlot.COMMUNICATION_STYLE)
        context.active_tasks = await self.get_memory_slot(user_id, MemorySlot.ACTIVE_TASKS)
        
        # Optionally load flexible memories
        if include_flexible:
            flex_memories = await self.get_flexible_memories(user_id, tags=flexible_tags)
            context.flexible_memories = [
                {"key": m.key, "value": m.value, "tags": m.tags}
                for m in flex_memories
            ]
        
        return context


# Global singleton instance
memory_service = ZStyleMemoryService()
