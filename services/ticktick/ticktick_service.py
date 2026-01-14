from typing import Optional


class TickTickService:
    """
    Service for interacting with TickTick API
    Uses ticktick-py OAuth2 flow for authentication
    """

    async def authenticate_user(self, user_id: str, code: str) -> dict:
        """
        Complete OAuth flow and store credentials

        Args:
            user_id: Internal ZStyle user ID
            code: OAuth code from redirect
        
        Returns:
            dict with status and token info
        """
        pass

    async def get_tasks(self, user_id: str, project_id: Optional[str] = None) -> list[dict]:
        """
        Get tasks for user, optionally filtered by project

        Args:
            user_id: Internal ZStyle user ID
            project_id: Optional project ID to filter tasks

        Returns:
            list of task dictionaries
        """
        pass
    
    async def create_task(
        self, 
        **kwargs: dict
        ) -> dict:
        """
        Create a new task

        Args:
            **kwargs: Task creation parameters

        Returns:
            dict with status and task info
        """
        pass

    async def update_task(
        self,
        task_id: str,
        **kwargs: dict
    ) -> dict:
        """
        Update an existing task
        """
        pass
    
    async def delete_task(
        self,
        task_id: str
    ) -> dict:
        """
        Delete an existing task
        """
        pass
    
    async def get_projects(self, user_id: str) -> list[dict]:
        """
        Get projects for user
        """
        pass
    
    async def create_project(
        self,
        **kwargs: dict
    ) -> dict:
        """
        Create a new project
        """
        pass