"""
API Routes

FastAPI router for API endpoints including health check and user state.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.exc import SQLAlchemyError

from core.database.engine import get_db_session
from core.database.repositories.user_repository import UserRepository
from core.database.models import User, ActivityLog
from core.database.models.memory import UserMemory

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Get agents directory (same as in main.py)
agent_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/agents"
AGENTS_DIR = str(agent_directory)


@router.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration.
    """
    return {
        "status": "healthy",
        "service": "zstyle-services",
        "agents_dir": AGENTS_DIR
    }


@router.get("/user/state")
async def get_user_state(
    user_id: str = Query(..., description="User ID to retrieve state for"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user state including profile, recent activity, and memory summary.
    
    Returns:
        Combined user state with:
        - profile: User profile information
        - recent_activity: Last 10 activity log entries
        - memory_summary: Total and recent memory counts
    """
    try:
        # Get user from repository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
        
        # Query recent activity logs (last 10)
        activity_stmt = select(ActivityLog).where(
            ActivityLog.user_id == user_id
        ).order_by(desc(ActivityLog.timestamp)).limit(10)
        
        activity_result = await db.execute(activity_stmt)
        recent_logs = activity_result.scalars().all()
        
        # Query memory counts
        # Total memories
        memory_count_stmt = select(func.count(UserMemory.id)).where(
            UserMemory.user_id == user_id
        )
        memory_count_result = await db.execute(memory_count_stmt)
        memory_count = memory_count_result.scalar() or 0
        
        # Recent memories (last 7 days)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_memory_count_stmt = select(func.count(UserMemory.id)).where(
            UserMemory.user_id == user_id,
            UserMemory.created_at >= recent_cutoff
        )
        recent_memory_count_result = await db.execute(recent_memory_count_stmt)
        recent_memory_count = recent_memory_count_result.scalar() or 0
        
        # Build response
        return {
            "user_id": user.id,
            "profile": {
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "telegram_id": user.telegram_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            },
            "recent_activity": [
                {
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "source": log.source,
                    "action": log.action
                }
                for log in recent_logs
            ],
            "memory_summary": {
                "total_memories": memory_count,
                "recent_memories": recent_memory_count
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_user_state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error in get_user_state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
