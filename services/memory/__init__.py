"""
ZStyle Memory Service Package

Provides the memory-first architecture for user context management.

Usage:
    from services.memory import memory_service
    
    # Get user context for agent injection
    context = await memory_service.get_user_context(user_id="user123")
    
    # Access standardized slots
    goal = await memory_service.get_memory_slot(user_id, MemorySlot.CURRENT_GOAL)
"""
from .memory_service import memory_service, ZStyleMemoryService, UserContext

__all__ = ["memory_service", "ZStyleMemoryService", "UserContext"]
