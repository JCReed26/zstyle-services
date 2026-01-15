"""
TickTick Service

Service for interacting with TickTick API using ticktick-py library.
Handles OAuth2 authentication and credential management via credential_service.
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ticktick.oauth2 import OAuth2
from ticktick.api import TickTickClient

from services import credential_service
from services.credential_service import CredentialNotFoundError
from core.config import settings


class TickTickService:
    """
    Service for interacting with TickTick API
    Uses ticktick-py OAuth2 flow for authentication
    """
    
    def __init__(self):
        """Initialize TickTickService with OAuth2 configuration."""
        self.client_id = settings.TICKTICK_CLIENT_ID
        self.client_secret = settings.TICKTICK_CLIENT_SECRET
        self.redirect_uri = "http://localhost:8080/redirect"  # Default redirect URI
        
        if self.client_id and self.client_secret:
            self.oauth_client = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri
            )
        else:
            self.oauth_client = None
    
    async def _get_client(self, user_id: str) -> TickTickClient:
        """
        Get TickTickClient instance for a user.
        
        Args:
            user_id: Internal ZStyle user ID
            
        Returns:
            TickTickClient instance
            
        Raises:
            CredentialNotFoundError: If credentials not found
        """
        credentials = await credential_service.get_credentials(user_id, "ticktick")
        
        if not credentials:
            raise CredentialNotFoundError(
                f"No TickTick credentials found for user {user_id}. "
                "Please authenticate first using authenticate_user()."
            )
        
        # Extract credentials
        username = credentials.get("username")
        password = credentials.get("password")
        access_token = credentials.get("token") or credentials.get("access_token")
        
        # If we have username/password, use them
        if username and password:
            return TickTickClient(username, password, self.oauth_client)
        
        # If we only have tokens, we might need to refresh or re-authenticate
        # For now, raise error if we don't have username/password
        # (ticktick-py requires username/password for client initialization)
        if not username or not password:
            raise CredentialNotFoundError(
                f"Incomplete TickTick credentials for user {user_id}. "
                "Username and password are required."
            )
        
        return TickTickClient(username, password, self.oauth_client)
    
    async def authenticate_user(self, user_id: str, code: str) -> dict:
        """
        Complete OAuth flow and store credentials

        Args:
            user_id: Internal ZStyle user ID
            code: OAuth code from redirect
        
        Returns:
            dict with status and token info
            
        Raises:
            ValueError: If code is empty or invalid
        """
        if not code or not code.strip():
            raise ValueError("OAuth code is required")
        
        if not self.oauth_client:
            raise ValueError(
                "TickTick OAuth not configured. "
                "Please set TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET in environment."
            )
        
        try:
            # Exchange code for tokens
            token_response = await asyncio.to_thread(
                self.oauth_client.get_access_token,
                code
            )
            
            # Extract token information
            access_token = token_response.get("access_token")
            refresh_token = token_response.get("refresh_token")
            expires_in = token_response.get("expires_in", 3600)
            
            # Calculate expiration timestamp
            expires_at = int(datetime.now().timestamp()) + expires_in
            
            # Store credentials
            credentials_to_store = {
                "token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "expires_in": expires_in
            }
            
            # Note: ticktick-py requires username/password for client initialization
            # So we might need to store those separately or get them from user
            # For now, store what we have from OAuth
            
            await credential_service.store_credentials(
                user_id=user_id,
                service="ticktick",
                credentials=credentials_to_store
            )
            
            return {
                "status": "success",
                "access_token": access_token,
                "expires_at": expires_at,
                "expires_in": expires_in
            }
            
        except Exception as e:
            raise ValueError(f"Failed to authenticate user: {str(e)}") from e
    
    async def get_tasks(self, user_id: str, project_id: Optional[str] = None) -> list[dict]:
        """
        Get tasks for user, optionally filtered by project

        Args:
            user_id: Internal ZStyle user ID
            project_id: Optional project ID to filter tasks

        Returns:
            list of task dictionaries
            
        Raises:
            CredentialNotFoundError: If credentials not found
        """
        try:
            client = await self._get_client(user_id)
            
            if project_id:
                # Filter by project
                tasks = await asyncio.to_thread(
                    client.get_by_fields,
                    projectId=project_id,
                    search="tasks"
                )
            else:
                # Get all tasks
                tasks = await asyncio.to_thread(
                    client.get_by_fields,
                    search="tasks"
                )
            
            # Ensure we return a list
            if tasks is None:
                return []
            
            # Convert to list of dicts if needed
            if isinstance(tasks, list):
                return [dict(task) if not isinstance(task, dict) else task for task in tasks]
            
            return []
            
        except CredentialNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to get tasks: {str(e)}") from e
    
    async def create_task(
        self, 
        user_id: str,
        **kwargs: Any
    ) -> dict:
        """
        Create a new task

        Args:
            user_id: Internal ZStyle user ID
            **kwargs: Task creation parameters
                - title: Task title (required)
                - start: Start datetime (optional)
                - due_date: Due date (optional)
                - project_id: Project ID (optional)
                - priority: Priority level (optional)
                - description: Task description (optional)

        Returns:
            dict with task info
            
        Raises:
            CredentialNotFoundError: If credentials not found
            ValueError: If required fields missing or invalid
        """
        if not kwargs.get("title"):
            raise ValueError("Task title is required")
        
        try:
            client = await self._get_client(user_id)
            
            # Extract task parameters
            title = kwargs.get("title")
            start = kwargs.get("start") or kwargs.get("due_date")
            project_id = kwargs.get("project_id")
            priority = kwargs.get("priority")
            description = kwargs.get("description")
            
            # Create task
            task = await asyncio.to_thread(
                client.task.create,
                title,
                start=start,
                project_id=project_id,
                priority=priority,
                description=description
            )
            
            # Convert to dict if needed
            if isinstance(task, dict):
                return task
            return dict(task) if hasattr(task, '__dict__') else {"id": str(task)}
            
        except CredentialNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to create task: {str(e)}") from e
    
    async def update_task(
        self,
        user_id: str,
        task_id: str,
        **kwargs: Any
    ) -> dict:
        """
        Update an existing task
        
        Args:
            user_id: Internal ZStyle user ID
            task_id: Task ID to update
            **kwargs: Task fields to update
            
        Returns:
            dict with updated task info
            
        Raises:
            CredentialNotFoundError: If credentials not found
            ValueError: If task not found or update fails
        """
        try:
            client = await self._get_client(user_id)
            
            # Get existing task
            tasks = await asyncio.to_thread(
                client.get_by_fields,
                id=task_id,
                search="tasks"
            )
            
            if not tasks or len(tasks) == 0:
                raise ValueError(f"Task {task_id} not found")
            
            task = tasks[0] if isinstance(tasks, list) else tasks
            
            # Ensure task is a dict-like object
            if not isinstance(task, dict):
                task = dict(task) if hasattr(task, '__dict__') else {"id": task_id}
            
            # Update task fields
            for key, value in kwargs.items():
                if value is not None:
                    # Map our parameter names to TickTick field names
                    field_map = {
                        "title": "title",
                        "due_date": "dueDate",
                        "start_date": "startDate",
                        "project_id": "projectId",
                        "priority": "priority",
                        "status": "status",
                        "description": "content"
                    }
                    
                    ticktick_field = field_map.get(key, key)
                    task[ticktick_field] = value
            
            # Update task
            updated_task = await asyncio.to_thread(
                client.task.update,
                task
            )
            
            # Convert to dict if needed
            if isinstance(updated_task, dict):
                return updated_task
            return dict(updated_task) if hasattr(updated_task, '__dict__') else task
            
        except CredentialNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update task: {str(e)}") from e
    
    async def delete_task(
        self,
        user_id: str,
        task_id: str
    ) -> dict:
        """
        Delete an existing task
        
        Args:
            user_id: Internal ZStyle user ID
            task_id: Task ID to delete
            
        Returns:
            dict with deletion status
            
        Raises:
            CredentialNotFoundError: If credentials not found
            ValueError: If task not found or deletion fails
        """
        try:
            client = await self._get_client(user_id)
            
            # Get task first to verify it exists
            tasks = await asyncio.to_thread(
                client.get_by_fields,
                id=task_id,
                search="tasks"
            )
            
            if not tasks or len(tasks) == 0:
                raise ValueError(f"Task {task_id} not found")
            
            task = tasks[0]
            
            # Delete task
            result = await asyncio.to_thread(
                client.task.delete,
                task
            )
            
            return {
                "status": "success",
                "deleted": True,
                "task_id": task_id
            }
            
        except CredentialNotFoundError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete task: {str(e)}") from e
    
    async def get_projects(self, user_id: str) -> list[dict]:
        """
        Get projects for user
        
        Args:
            user_id: Internal ZStyle user ID
            
        Returns:
            list of project dictionaries
            
        Raises:
            CredentialNotFoundError: If credentials not found
        """
        try:
            client = await self._get_client(user_id)
            
            # Get all projects
            projects = await asyncio.to_thread(
                client.project.get_all
            )
            
            # Ensure we return a list
            if projects is None:
                return []
            
            # Convert to list of dicts if needed
            if isinstance(projects, list):
                return [dict(p) if not isinstance(p, dict) else p for p in projects]
            
            return []
            
        except CredentialNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to get projects: {str(e)}") from e
    
    async def create_project(
        self,
        user_id: str,
        **kwargs: Any
    ) -> dict:
        """
        Create a new project
        
        Args:
            user_id: Internal ZStyle user ID
            **kwargs: Project creation parameters
                - name: Project name (required)
                - color: Project color (optional)
                - is_archived: Whether project is archived (optional)
        
        Returns:
            dict with project info
            
        Raises:
            CredentialNotFoundError: If credentials not found
            ValueError: If required fields missing or invalid
        """
        if not kwargs.get("name"):
            raise ValueError("Project name is required")
        
        try:
            client = await self._get_client(user_id)
            
            # Extract project parameters
            name = kwargs.get("name")
            color = kwargs.get("color")
            is_archived = kwargs.get("is_archived", False)
            
            # Create project
            project = await asyncio.to_thread(
                client.project.create,
                name,
                color=color,
                is_archived=is_archived
            )
            
            # Convert to dict if needed
            if isinstance(project, dict):
                return project
            return dict(project) if hasattr(project, '__dict__') else {"name": name}
            
        except CredentialNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to create project: {str(e)}") from e
