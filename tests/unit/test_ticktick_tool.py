"""
Unit tests for TickTickTool.

Following TDD principles - these tests are written before implementation.
Tests mock TickTickService to verify tool behavior and error handling.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from tools.ticktick_tool import TickTickTool
from services.credential_service import CredentialNotFoundError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def ticktick_tool():
    """Create a TickTickTool instance."""
    return TickTickTool()


@pytest.fixture
def mock_ticktick_service():
    """Mock TickTickService instance."""
    service = MagicMock()
    service.create_task = AsyncMock()
    service.get_tasks = AsyncMock()
    service.get_projects = AsyncMock()
    return service


# ============================================================================
# ADD TASK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_add_task_success(ticktick_tool, mock_ticktick_service):
    """Test successfully creating a task."""
    test_user_id = "user123"
    test_title = "Test Task"
    
    mock_result = {"id": "task123", "title": test_title}
    mock_ticktick_service.create_task.return_value = mock_result
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.add_task(test_user_id, test_title)
        
        assert "Success" in result
        assert test_title in result
        assert "task123" in result
        mock_ticktick_service.create_task.assert_called_once_with(
            test_user_id,
            title=test_title,
            description=None,
            due_date=None
        )


@pytest.mark.asyncio
async def test_add_task_with_all_fields(ticktick_tool, mock_ticktick_service):
    """Test creating task with all fields (title, content, due_date)."""
    test_user_id = "user123"
    test_title = "Complete Task"
    test_content = "Task description"
    test_due_date = "2024-12-31"
    
    mock_result = {"id": "task456", "title": test_title}
    mock_ticktick_service.create_task.return_value = mock_result
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.add_task(
            test_user_id,
            test_title,
            content=test_content,
            due_date=test_due_date
        )
        
        assert "Success" in result
        assert test_title in result
        mock_ticktick_service.create_task.assert_called_once_with(
            test_user_id,
            title=test_title,
            description=test_content,
            due_date=test_due_date
        )


@pytest.mark.asyncio
async def test_add_task_no_credentials(ticktick_tool, mock_ticktick_service):
    """Test creating task without credentials returns error message."""
    test_user_id = "user123"
    test_title = "Test Task"
    
    mock_ticktick_service.create_task.side_effect = CredentialNotFoundError(
        "No credentials found"
    )
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.add_task(test_user_id, test_title)
        
        assert "Error" in result
        assert "credentials" in result.lower() or "credential" in result.lower()
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_add_task_service_error(ticktick_tool, mock_ticktick_service):
    """Test handling service exceptions gracefully."""
    test_user_id = "user123"
    test_title = "Test Task"
    
    mock_ticktick_service.create_task.side_effect = ValueError("Invalid task data")
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.add_task(test_user_id, test_title)
        
        assert "Error" in result
        assert isinstance(result, str)


# ============================================================================
# GET TASKS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_tasks_success(ticktick_tool, mock_ticktick_service):
    """Test successfully retrieving tasks (default Inbox - all tasks)."""
    test_user_id = "user123"
    mock_tasks = [
        {"id": "task1", "title": "Task 1", "status": 0},
        {"id": "task2", "title": "Task 2", "status": 0}
    ]
    
    mock_ticktick_service.get_tasks.return_value = mock_tasks
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id)
        
        assert isinstance(result, str)
        # Should contain task information
        assert "task1" in result or "Task 1" in result
        mock_ticktick_service.get_tasks.assert_called_once_with(
            test_user_id,
            project_id=None
        )


@pytest.mark.asyncio
async def test_get_tasks_with_list_name(ticktick_tool, mock_ticktick_service):
    """Test retrieving tasks filtered by list_name (maps to project_id)."""
    test_user_id = "user123"
    test_list_name = "Work"
    test_project_id = "project123"
    
    mock_projects = [
        {"id": test_project_id, "name": "Work"},
        {"id": "project456", "name": "Personal"}
    ]
    mock_tasks = [{"id": "task1", "title": "Work Task", "projectId": test_project_id}]
    
    mock_ticktick_service.get_projects.return_value = mock_projects
    mock_ticktick_service.get_tasks.return_value = mock_tasks
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id, list_name=test_list_name)
        
        assert isinstance(result, str)
        # Should have looked up projects
        mock_ticktick_service.get_projects.assert_called_once_with(test_user_id)
        # Should have called get_tasks with project_id
        mock_ticktick_service.get_tasks.assert_called_once_with(
            test_user_id,
            project_id=test_project_id
        )


@pytest.mark.asyncio
async def test_get_tasks_list_name_not_found(ticktick_tool, mock_ticktick_service):
    """Test handling invalid list_name returns error message."""
    test_user_id = "user123"
    test_list_name = "NonExistentList"
    
    mock_projects = [
        {"id": "project1", "name": "Work"},
        {"id": "project2", "name": "Personal"}
    ]
    
    mock_ticktick_service.get_projects.return_value = mock_projects
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id, list_name=test_list_name)
        
        assert "Error" in result
        assert test_list_name in result
        assert "not found" in result.lower()
        # Should not have called get_tasks
        mock_ticktick_service.get_tasks.assert_not_called()


@pytest.mark.asyncio
async def test_get_tasks_no_credentials(ticktick_tool, mock_ticktick_service):
    """Test retrieving tasks without credentials returns error message."""
    test_user_id = "user123"
    
    mock_ticktick_service.get_tasks.side_effect = CredentialNotFoundError(
        "No credentials found"
    )
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id)
        
        assert "Error" in result
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_get_tasks_empty_result(ticktick_tool, mock_ticktick_service):
    """Test handling empty task lists."""
    test_user_id = "user123"
    
    mock_ticktick_service.get_tasks.return_value = []
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id)
        
        assert isinstance(result, str)
        # Should handle empty list gracefully
        assert len(result) > 0


@pytest.mark.asyncio
async def test_get_tasks_list_name_case_insensitive(ticktick_tool, mock_ticktick_service):
    """Test that list_name matching is case-insensitive."""
    test_user_id = "user123"
    test_list_name = "WORK"  # Uppercase
    test_project_id = "project123"
    
    mock_projects = [
        {"id": test_project_id, "name": "Work"},  # Mixed case
        {"id": "project456", "name": "Personal"}
    ]
    mock_tasks = [{"id": "task1", "title": "Work Task"}]
    
    mock_ticktick_service.get_projects.return_value = mock_projects
    mock_ticktick_service.get_tasks.return_value = mock_tasks
    
    with patch.object(ticktick_tool, 'service', mock_ticktick_service):
        result = await ticktick_tool.get_tasks(test_user_id, list_name=test_list_name)
        
        # Should find the project despite case difference
        assert "Error" not in result or "not found" not in result.lower()
        mock_ticktick_service.get_tasks.assert_called_once_with(
            test_user_id,
            project_id=test_project_id
        )
