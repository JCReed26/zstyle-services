"""
Unit tests for TickTickService.

Following TDD principles - these tests are written before implementation.
Tests mock external dependencies (credential_service, ticktick-py library).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any, Optional

from services.ticktick.ticktick_service import TickTickService
from services.credential_service import CredentialNotFoundError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def ticktick_service():
    """Create a TickTickService instance."""
    return TickTickService()


@pytest.fixture
def mock_credentials():
    """Mock credentials dictionary."""
    return {
        "token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "username": "test@example.com",
        "password": "test_password",
        "expires_at": 9999999999
    }


@pytest.fixture
def mock_ticktick_client():
    """Mock TickTickClient instance."""
    client = MagicMock()
    client.task = MagicMock()
    client.project = MagicMock()
    client.get_by_fields = MagicMock()
    return client


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_authenticate_user_success(ticktick_service, mock_credentials):
    """Test successful OAuth authentication flow."""
    test_code = "test_oauth_code"
    test_user_id = "user123"
    
    mock_token_response = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 3600
    }
    
    with patch('services.ticktick.ticktick_service.OAuth2') as mock_oauth_class, \
         patch('services.ticktick.ticktick_service.credential_service') as mock_cred_service:
        
        # Setup OAuth2 mock
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.get_access_token.return_value = mock_token_response
        mock_oauth_class.return_value = mock_oauth_instance
        
        # Setup credential service mock
        mock_cred_service.store_credentials = AsyncMock()
        
        # Execute
        result = await ticktick_service.authenticate_user(test_user_id, test_code)
        
        # Verify
        assert result is not None
        assert "status" in result or "access_token" in result
        mock_oauth_instance.get_access_token.assert_called_once_with(test_code)
        mock_cred_service.store_credentials.assert_called_once()
        
        # Verify stored credentials format
        call_args = mock_cred_service.store_credentials.call_args
        assert call_args[1]["user_id"] == test_user_id
        assert call_args[1]["service"] == "ticktick"
        stored_creds = call_args[1]["credentials"]
        assert "token" in stored_creds or "access_token" in stored_creds


@pytest.mark.asyncio
async def test_authenticate_user_missing_code(ticktick_service):
    """Test authentication with missing code raises ValueError."""
    with pytest.raises(ValueError):
        await ticktick_service.authenticate_user("user123", "")


@pytest.mark.asyncio
async def test_authenticate_user_invalid_code(ticktick_service):
    """Test authentication with invalid code handles errors gracefully."""
    test_code = "invalid_code"
    test_user_id = "user123"
    
    with patch('services.ticktick.ticktick_service.OAuth2') as mock_oauth_class:
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.get_access_token.side_effect = Exception("Invalid code")
        mock_oauth_class.return_value = mock_oauth_instance
        
        with pytest.raises(Exception):
            await ticktick_service.authenticate_user(test_user_id, test_code)


@pytest.mark.asyncio
async def test_authenticate_user_stores_refresh_token(ticktick_service):
    """Test that refresh token is stored correctly."""
    test_code = "test_code"
    test_user_id = "user123"
    
    mock_token_response = {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }
    
    with patch('services.ticktick.ticktick_service.OAuth2') as mock_oauth_class, \
         patch('services.ticktick.ticktick_service.credential_service') as mock_cred_service:
        
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.get_access_token.return_value = mock_token_response
        mock_oauth_class.return_value = mock_oauth_instance
        mock_cred_service.store_credentials = AsyncMock()
        
        await ticktick_service.authenticate_user(test_user_id, test_code)
        
        # Verify refresh token was stored
        call_args = mock_cred_service.store_credentials.call_args
        stored_creds = call_args[1]["credentials"]
        assert "refresh_token" in stored_creds
        assert stored_creds["refresh_token"] == "refresh_token"


# ============================================================================
# GET TASKS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_tasks_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully retrieving tasks."""
    test_user_id = "user123"
    mock_tasks = [
        {"id": "task1", "title": "Task 1", "status": 0},
        {"id": "task2", "title": "Task 2", "status": 0}
    ]
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.get_by_fields.return_value = mock_tasks
        mock_to_thread.return_value = mock_tasks
        
        result = await ticktick_service.get_tasks(test_user_id)
        
        assert isinstance(result, list)
        assert len(result) == 2
        mock_get_client.assert_called_once_with(test_user_id)


@pytest.mark.asyncio
async def test_get_tasks_with_project_filter(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test retrieving tasks filtered by project_id."""
    test_user_id = "user123"
    test_project_id = "project123"
    mock_tasks = [{"id": "task1", "title": "Task 1", "projectId": test_project_id}]
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.get_by_fields.return_value = mock_tasks
        mock_to_thread.return_value = mock_tasks
        
        result = await ticktick_service.get_tasks(test_user_id, project_id=test_project_id)
        
        assert isinstance(result, list)
        assert len(result) == 1


@pytest.mark.asyncio
async def test_get_tasks_no_credentials(ticktick_service):
    """Test that missing credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch('services.ticktick_service.credential_service') as mock_cred_service:
        mock_cred_service.get_credentials = AsyncMock(return_value=None)
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.get_tasks(test_user_id)


@pytest.mark.asyncio
async def test_get_tasks_empty_list(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test retrieving tasks when user has no tasks."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.get_by_fields.return_value = []
        mock_to_thread.return_value = []
        
        result = await ticktick_service.get_tasks(test_user_id)
        
        assert isinstance(result, list)
        assert len(result) == 0


# ============================================================================
# CREATE TASK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_task_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully creating a task."""
    test_user_id = "user123"
    task_data = {
        "title": "New Task",
        "due_date": "2024-12-31"
    }
    mock_created_task = {"id": "new_task_id", "title": "New Task", "status": 0}
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.task.create.return_value = mock_created_task
        mock_to_thread.return_value = mock_created_task
        
        result = await ticktick_service.create_task(user_id=test_user_id, **task_data)
        
        assert isinstance(result, dict)
        assert result["id"] == "new_task_id"
        assert result["title"] == "New Task"


@pytest.mark.asyncio
async def test_create_task_with_all_fields(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test creating task with all possible fields."""
    test_user_id = "user123"
    task_data = {
        "title": "Complete Task",
        "due_date": "2024-12-31",
        "project_id": "project123",
        "priority": 3,
        "description": "Task description"
    }
    mock_created_task = {"id": "task_id", **task_data}
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.task.create.return_value = mock_created_task
        mock_to_thread.return_value = mock_created_task
        
        result = await ticktick_service.create_task(user_id=test_user_id, **task_data)
        
        assert result["title"] == "Complete Task"
        assert result["project_id"] == "project123"


@pytest.mark.asyncio
async def test_create_task_no_credentials(ticktick_service):
    """Test creating task without credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.side_effect = CredentialNotFoundError("No credentials")
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.create_task(user_id=test_user_id, title="Task")


@pytest.mark.asyncio
async def test_create_task_invalid_data(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test creating task with invalid data handles API errors."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_to_thread.side_effect = ValueError("Invalid task data")
        
        with pytest.raises(ValueError):
            await ticktick_service.create_task(user_id=test_user_id, title="")


# ============================================================================
# UPDATE TASK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_task_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully updating a task."""
    test_user_id = "user123"
    test_task_id = "task123"
    update_data = {"title": "Updated Title", "status": 1}
    
    mock_existing_task = {"id": test_task_id, "title": "Original Title", "status": 0}
    mock_updated_task = {**mock_existing_task, **update_data}
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        
        # Mock getting task and updating it
        def to_thread_side_effect(func, *args, **kwargs):
            if 'get_by_fields' in str(func) or 'task.get' in str(func):
                return [mock_existing_task]
            elif 'task.update' in str(func) or 'update' in str(func):
                return mock_updated_task
            return None
        
        mock_to_thread.side_effect = to_thread_side_effect
        mock_ticktick_client.get_by_fields.return_value = [mock_existing_task]
        mock_ticktick_client.task.update.return_value = mock_updated_task
        
        result = await ticktick_service.update_task(test_user_id, test_task_id, **update_data)
        
        assert isinstance(result, dict)
        assert result["title"] == "Updated Title"
        assert result["status"] == 1


@pytest.mark.asyncio
async def test_update_task_not_found(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test updating non-existent task handles error."""
    test_user_id = "user123"
    test_task_id = "nonexistent_task"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.get_by_fields.return_value = []
        mock_to_thread.return_value = []
        
        with pytest.raises(ValueError, match="not found|NotFound"):
            await ticktick_service.update_task(test_user_id, test_task_id, title="New Title")


@pytest.mark.asyncio
async def test_update_task_no_credentials(ticktick_service):
    """Test updating task without credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.side_effect = CredentialNotFoundError("No credentials")
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.update_task(test_user_id, "task123", title="New Title")


# ============================================================================
# DELETE TASK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delete_task_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully deleting a task."""
    test_user_id = "user123"
    test_task_id = "task123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.task.delete.return_value = True
        mock_to_thread.return_value = True
        
        result = await ticktick_service.delete_task(test_user_id, test_task_id)
        
        assert isinstance(result, dict)
        assert "status" in result or "success" in result or result.get("deleted") is True


@pytest.mark.asyncio
async def test_delete_task_not_found(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test deleting non-existent task handles error gracefully."""
    test_user_id = "user123"
    test_task_id = "nonexistent_task"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_to_thread.side_effect = ValueError("Task not found")
        
        with pytest.raises(ValueError):
            await ticktick_service.delete_task(test_user_id, test_task_id)


@pytest.mark.asyncio
async def test_delete_task_no_credentials(ticktick_service):
    """Test deleting task without credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.side_effect = CredentialNotFoundError("No credentials")
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.delete_task(test_user_id, "task123")


# ============================================================================
# GET PROJECTS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_projects_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully retrieving projects."""
    test_user_id = "user123"
    mock_projects = [
        {"id": "project1", "name": "Project 1"},
        {"id": "project2", "name": "Project 2"}
    ]
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.project.get_all.return_value = mock_projects
        mock_to_thread.return_value = mock_projects
        
        result = await ticktick_service.get_projects(test_user_id)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Project 1"


@pytest.mark.asyncio
async def test_get_projects_no_credentials(ticktick_service):
    """Test retrieving projects without credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.side_effect = CredentialNotFoundError("No credentials")
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.get_projects(test_user_id)


# ============================================================================
# CREATE PROJECT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_project_success(ticktick_service, mock_credentials, mock_ticktick_client):
    """Test successfully creating a project."""
    test_user_id = "user123"
    project_data = {"name": "New Project"}
    mock_created_project = {"id": "new_project_id", "name": "New Project"}
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client, \
         patch('asyncio.to_thread') as mock_to_thread:
        
        mock_get_client.return_value = mock_ticktick_client
        mock_ticktick_client.project.create.return_value = mock_created_project
        mock_to_thread.return_value = mock_created_project
        
        result = await ticktick_service.create_project(user_id=test_user_id, **project_data)
        
        assert isinstance(result, dict)
        assert result["id"] == "new_project_id"
        assert result["name"] == "New Project"


@pytest.mark.asyncio
async def test_create_project_no_credentials(ticktick_service):
    """Test creating project without credentials raises CredentialNotFoundError."""
    test_user_id = "user123"
    
    with patch.object(ticktick_service, '_get_client', new_callable=AsyncMock) as mock_get_client:
        mock_get_client.side_effect = CredentialNotFoundError("No credentials")
        
        with pytest.raises(CredentialNotFoundError):
            await ticktick_service.create_project(user_id=test_user_id, name="Project")
