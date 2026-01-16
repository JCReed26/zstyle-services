"""
TickTick Tool for Google ADK

Wraps TickTickService methods as Google ADK tools for the exec_func_coach agent.
Provides add_task and get_tasks functionality.
"""
import json
from typing import Optional

from services.ticktick.ticktick_service import TickTickService
from services.credential_service import CredentialNotFoundError


class TickTickTool:
    """
    Tool class that wraps TickTickService methods as Google ADK tools.
    
    Provides:
    - add_task: Create a new TickTick task
    - get_tasks: Retrieve tasks, optionally filtered by list_name
    """
    
    def __init__(self):
        """Initialize TickTickTool with TickTickService instance."""
        # #region debug log
        try:
            import json, time
            with open('/tmp/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"ticktick_tool.py:23","message":"TickTickTool.__init__ entry","data":{},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        self.service = TickTickService()
        # #region debug log
        try:
            import json, time
            with open('/tmp/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"ticktick_tool.py:25","message":"TickTickTool.__init__ exit","data":{},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
    
    async def add_task(
        self,
        user_id: str,
        title: str,
        content: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> str:
        """
        Create a new TickTick task.
        
        Args:
            user_id: Internal ZStyle user ID
            title: Task title (required)
            content: Task description/content (optional)
            due_date: Task due date (optional)
        
        Returns:
            Success message with task ID, or error message
        """
        try:
            result = await self.service.create_task(
                user_id,
                title=title,
                description=content,
                due_date=due_date
            )
            
            task_id = result.get("id", "unknown")
            return f"Success: Task '{title}' created. ID: {task_id}"
            
        except CredentialNotFoundError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def get_tasks(self, user_id: str, list_name: str = "Inbox") -> str:
        """
        Get TickTick tasks, optionally filtered by list_name.
        
        Args:
            user_id: Internal ZStyle user ID
            list_name: List/project name to filter by (default: "Inbox" for all tasks)
        
        Returns:
            JSON string of tasks, or error message
        """
        try:
            # Map list_name to project_id
            project_id = None
            
            # If list_name is "Inbox" or empty, get all tasks (no project filter)
            if list_name and list_name.lower() != "inbox":
                # Look up project by name
                projects = await self.service.get_projects(user_id)
                
                # Find project matching list_name (case-insensitive)
                matching_project = None
                for project in projects:
                    project_name = project.get("name", "")
                    if project_name.lower() == list_name.lower():
                        matching_project = project
                        break
                
                if matching_project:
                    project_id = matching_project.get("id")
                else:
                    return f"Error: List '{list_name}' not found"
            
            # Get tasks
            tasks = await self.service.get_tasks(user_id, project_id=project_id)
            
            # Format tasks as JSON string
            if not tasks:
                return "No tasks found."
            
            # Return formatted JSON string
            return json.dumps(tasks, indent=2, default=str)
            
        except CredentialNotFoundError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
