"""
Activity Log Service

Provides logging and retrieval of user activity for transparency.
Users can view their recent activity or export all logs.

Supports graceful degradation - logs to console if database unavailable.

USAGE EXAMPLE:
==============
from services.activity_log import activity_log_service, ActivityLogSource

# Log an activity
await activity_log_service.log(
    user_id="user123",
    source=ActivityLogSource.TELEGRAM,
    action="user inquired about today's schedule"
)

# Get recent logs
recent = await activity_log_service.get_recent(user_id="user123", limit=25)

# Export all logs (for email attachment)
export_text = await activity_log_service.export_all(user_id="user123")
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database.engine import AsyncSessionLocal
from database.models import ActivityLog, ActivityLogSource
from database.availability import is_database_available

logger = logging.getLogger(__name__)


class ActivityLogService:
    """
    Service for logging and retrieving user activity.
    
    All significant system actions should be logged:
    - User messages (via any channel)
    - Automated actions (cron jobs, webhooks)
    - Agent tool executions
    - System events affecting the user
    """

    async def log(
        self,
        user_id: str,
        source: str | ActivityLogSource,
        action: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Optional[ActivityLog]:
        """
        Create a new activity log entry.
        
        If database is unavailable, logs to console instead.
        
        Args:
            user_id: The user's ID
            source: Source type (use ActivityLogSource enum)
            action: Human-readable description of what happened
            extra_data: Optional structured data for filtering/analysis
            
        Returns:
            The created ActivityLog record, or None if database unavailable
            
        Example:
            await activity_log_service.log(
                user_id="user123",
                source=ActivityLogSource.TELEGRAM,
                action="user asked about calendar events"
            )
        """
        # Convert enum to string if needed
        if isinstance(source, ActivityLogSource):
            source = source.value
        
        if not is_database_available():
            # Log to console instead
            logger.info(f"[ActivityLog] {source} - {action} (user: {user_id})")
            return None
        
        try:
            async with AsyncSessionLocal() as db:
                log_entry = ActivityLog(
                    user_id=user_id,
                    source=source,
                    action=action,
                    extra_data=extra_data or {}
                )
                db.add(log_entry)
                await db.commit()
                await db.refresh(log_entry)
                return log_entry
        except Exception as e:
            logger.error(f"Failed to log activity: {e}", exc_info=True)
            # Fallback to console logging
            logger.info(f"[ActivityLog] {source} - {action} (user: {user_id})")
            return None

    async def get_recent(
        self,
        user_id: str,
        limit: int = 25,
        source_filter: Optional[str | ActivityLogSource] = None
    ) -> List[ActivityLog]:
        """
        Get the most recent activity logs for a user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of entries to return (default: 25)
            source_filter: Optional filter by source type
            
        Returns:
            List of ActivityLog records, most recent first (empty list if database unavailable)
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot retrieve activity logs for user {user_id}")
            return []
        
        if isinstance(source_filter, ActivityLogSource):
            source_filter = source_filter.value
        
        try:
            async with AsyncSessionLocal() as db:
                query = select(ActivityLog).where(
                    ActivityLog.user_id == user_id
                ).order_by(desc(ActivityLog.timestamp)).limit(limit)
                
                if source_filter:
                    query = query.where(ActivityLog.source == source_filter)
                
                result = await db.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to retrieve activity logs: {e}", exc_info=True)
            return []

    async def get_logs_in_range(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
        source_filter: Optional[str] = None
    ) -> List[ActivityLog]:
        """
        Get activity logs within a date range.
        
        Args:
            user_id: The user's ID
            start: Start of date range
            end: End of date range
            source_filter: Optional filter by source type
            
        Returns:
            List of ActivityLog records within the range (empty list if database unavailable)
        """
        if not is_database_available():
            logger.warning(f"Database unavailable - cannot retrieve activity logs for user {user_id}")
            return []
        
        try:
            async with AsyncSessionLocal() as db:
                query = select(ActivityLog).where(
                    ActivityLog.user_id == user_id,
                    ActivityLog.timestamp >= start,
                    ActivityLog.timestamp <= end
                ).order_by(desc(ActivityLog.timestamp))
                
                if source_filter:
                    query = query.where(ActivityLog.source == source_filter)
                
                result = await db.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to retrieve activity logs: {e}", exc_info=True)
            return []

    async def export_all(
        self,
        user_id: str,
        source_filter: Optional[str] = None
    ) -> str:
        """
        Export all logs as formatted text (for email attachment).
        
        Format: HH:MM:SS-YYYY-MM-DD - source - action
        
        Args:
            user_id: The user's ID
            source_filter: Optional filter by source type
            
        Returns:
            Formatted string of all log entries (or message if database unavailable)
        """
        if not is_database_available():
            return "Database unavailable - activity logs cannot be exported."
        
        try:
            async with AsyncSessionLocal() as db:
                query = select(ActivityLog).where(
                    ActivityLog.user_id == user_id
                ).order_by(ActivityLog.timestamp)
                
                if source_filter:
                    query = query.where(ActivityLog.source == source_filter)
                
                result = await db.execute(query)
                logs = result.scalars().all()
            
            if not logs:
                return "No activity logs found."
            
            lines = [
                "ZStyle Activity Log Export",
                f"User: {user_id}",
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Total Entries: {len(logs)}",
                "",
                "-" * 60,
                ""
            ]
            
            for log in logs:
                lines.append(log.format())
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Failed to export activity logs: {e}", exc_info=True)
            return "Error exporting activity logs."

    def format_logs_for_display(self, logs: List[ActivityLog]) -> str:
        """
        Format a list of logs for display (e.g., in Telegram message).
        
        Args:
            logs: List of ActivityLog records
            
        Returns:
            Formatted string suitable for chat display
        """
        if not logs:
            return "No recent activity."
        
        return "\n".join(log.format() for log in logs)


# Global singleton instance
activity_log_service = ActivityLogService()
