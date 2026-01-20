# ticktool.py
"""
TickTick Tool for the exec func coach 

implements the ticktick api using ticktick-py framework
"""

import logging
from typing import Optional, Dict, Any
from ticktick.oauth2 import OAuth2
from ticktick.api import TickTickClient
from services import credential_service
from app.config import settings

logger = logging.getLogger(__name__)


# imports
# (ticktick-py imports are above)


# helpers
async def get_ticktick_client(user_id: str) -> Optional[TickTickClient]:
    """Get TickTick client for user."""
    if not settings.TICKTICK_CLIENT_ID or not settings.TICKTICK_CLIENT_SECRET:
        return None
    
    creds = await credential_service.get_credentials(user_id, "ticktick")
    if not creds:
        return None
    
    auth = OAuth2(
        client_id=settings.TICKTICK_CLIENT_ID,
        client_secret=settings.TICKTICK_CLIENT_SECRET,
        redirect_uri=settings.TICKTICK_REDIRECT_URI or f"{settings.OAUTH_BASE_URL or 'http://localhost:8000'}/oauth/ticktick/callback"
    )
    auth.token = creds.get("token")
    auth.refresh_token = creds.get("refresh_token")
    
    client = TickTickClient(None, auth)
    try:
        client.sync()
        return client
    except Exception as e:
        logger.error(f"TickTick sync failed for {user_id}: {e}")
        return None


# oauth helpers
# (OAuth setup is handled in get_ticktick_client above)


# ticktick tool interface
# implement all of https://lazeroffmichael.github.io/ticktick-py/
class TickTickTool:
    """TickTick integration tool using ticktick-py framework."""
    

    async def add_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: int = 3,
    ) -> Dict[str, Any]:
        """Add task to TickTick."""
        client = await get_ticktick_client(user_id)
        if not client:
            return {"success": False, "error": "TickTick not authorized. Use /authorize to connect."}
        
        try:
            task_data = client.task.builder(title=title, content=description or "", priority=priority)
            task_data["projectId"] = project_id or client.inbox_id
            created = client.task.create(task_data)
            return {"success": True, "task": {"id": created.get("id"), "title": created.get("title")}}
        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    

    async def get_tasks(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get tasks from TickTick."""
        client = await get_ticktick_client(user_id)
        if not client:
            return {"success": False, "error": "TickTick not authorized. Use /authorize to connect.", "tasks": []}
        
        try:
            tasks = client.state.get("tasks", [])
            
            if project_id:
                tasks = [t for t in tasks if t.get("projectId") == project_id]
            if status == "completed":
                tasks = [t for t in tasks if t.get("status") == 2]
            elif status == "uncompleted":
                tasks = [t for t in tasks if t.get("status") != 2]
            if search:
                search_lower = search.lower()
                tasks = [t for t in tasks if search_lower in t.get("title", "").lower()]
            
            formatted = [
                {"id": t.get("id"), "title": t.get("title"), "status": "completed" if t.get("status") == 2 else "uncompleted"}
                for t in tasks
            ]
            return {"success": True, "tasks": formatted, "count": len(formatted)}
        except Exception as e:
            logger.error(f"Error getting tasks: {e}", exc_info=True)
            return {"success": False, "error": str(e), "tasks": []}
    

    async def update_task(
        self,
        user_id: str,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a TickTick task."""
        client = await get_ticktick_client(user_id)
        if not client:
            return {"success": False, "error": "TickTick not authorized. Use /authorize to connect."}
        
        try:
            task = client.get_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            if title:
                task["title"] = title
            if description:
                task["content"] = description
            if status == "completed":
                task["status"] = 2
            elif status == "uncompleted":
                task["status"] = 0
            if priority:
                task["priority"] = priority
            
            updated = client.task.update(task)
            return {"success": True, "task": {"id": updated.get("id"), "title": updated.get("title")}}
        except Exception as e:
            logger.error(f"Error updating task: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    

    async def delete_task(
        self,
        user_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """Delete a TickTick task."""
        client = await get_ticktick_client(user_id)
        if not client:
            return {"success": False, "error": "TickTick not authorized. Use /authorize to connect."}
        
        try:
            task = client.get_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            client.task.delete(task)
            return {"success": True, "message": "Task deleted"}
        except Exception as e:
            logger.error(f"Error deleting task: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    

    async def get_projects(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get TickTick projects."""
        client = await get_ticktick_client(user_id)
        if not client:
            return {"success": False, "error": "TickTick not authorized. Use /authorize to connect.", "projects": []}
        
        try:
            projects = client.state.get("projects", [])
            formatted = [{"id": p.get("id"), "name": p.get("name")} for p in projects]
            return {"success": True, "projects": formatted, "count": len(formatted)}
        except Exception as e:
            logger.error(f"Error getting projects: {e}", exc_info=True)
            return {"success": False, "error": str(e), "projects": []}


# Initialize tool instance
ticktick_tool = TickTickTool()


# prompt for using ticktick tool and store in variable TICKTICK_PROMPT
TICKTICK_PROMPT = """
TickTick Task Management Tool

Use TickTick tools to help users manage their tasks and projects:

AVAILABLE OPERATIONS:
- add_task: Create a new task with title, optional description, project, and priority (1=Low, 3=Medium, 5=High)
- get_tasks: Retrieve tasks with optional filters (project_id, status, search query)
- update_task: Modify existing tasks (title, description, status, priority)
- delete_task: Remove tasks
- get_projects: List all available projects

BEST PRACTICES:
- Always require user_id as the first parameter
- Use get_projects first to help users find project IDs
- Default priority is 3 (Medium) if not specified
- Status values: "completed" or "uncompleted"
- Tasks are synced automatically - no need to manually refresh

AUTHORIZATION:
- Users must authorize TickTick via /authorize command before using tools
- If authorization fails, prompt user to use /authorize command
"""