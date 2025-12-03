import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Memory
from database.sqlite_db import get_db_session


class MemoryService:
    def __init__(self):
        pass

    async def store_memory(
        self,
        db: AsyncSession,
        user_id: str,
        agent_name: str,
        content: str,
        memory_type: str = 'long_term',
        memory_metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """Store a new memory entry."""
        memory = Memory(
            user_id=user_id,
            agent_name=agent_name,
            memory_type=memory_type,
            content=content,
            memory_metadata=memory_metadata or {}
        )

        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def retrieve_memory(
        self,
        db: AsyncSession,
        user_id: str,
        memory_id: str
    ) -> Optional[Memory]:
        """Retrieve a specific memory by ID."""
        result = await db.execute(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def search_memory(
        self,
        db: AsyncSession,
        user_id: str,
        agent_name: Optional[str] = None,
        memory_type: Optional[str] = None,
        search_content: Optional[str] = None
    ) -> List[Memory]:
        """Search memories with optional filters."""
        query = select(Memory).where(Memory.user_id == user_id)
        
        if agent_name:
            query = query.where(Memory.agent_name == agent_name)
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        if search_content:
            query = query.where(Memory.content.contains(search_content))
        
        result = await db.execute(query)
        return result.scalars().all()

    async def update_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str,
        content: Optional[str] = None,
        memory_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Memory]:
        """Update an existing memory."""
        result = await db.execute(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.user_id == user_id
            )
        )
        memory = result.scalar_one_or_none()

        if not memory:
            return None

        if content is not None:
            memory.content = content
        if memory_metadata is not None:
            memory.memory_metadata = memory_metadata

        await db.commit()
        await db.refresh(memory)
        return memory

    async def delete_memory(
        self,
        db: AsyncSession,
        memory_id: str,
        user_id: str
    ) -> bool:
        """Delete a memory entry."""
        result = await db.execute(
            select(Memory).where(
                Memory.id == memory_id,
                Memory.user_id == user_id
            )
        )
        memory = result.scalar_one_or_none()
        
        if not memory:
            return False
            
        await db.delete(memory)
        await db.commit()
        return True

    async def get_all_memories_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        agent_name: Optional[str] = None
    ) -> List[Memory]:
        """Get all memories for a user, optionally filtered by agent."""
        query = select(Memory).where(Memory.user_id == user_id)
        if agent_name:
            query = query.where(Memory.agent_name == agent_name)
        
        result = await db.execute(query)
        return result.scalars().all()


# Global instance
memory_service = MemoryService()