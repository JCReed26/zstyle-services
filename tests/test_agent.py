import pytest
import uuid
from agents.exec_func_coach.agent import root_agent
from agents.exec_func_coach.tools import get_user_calendar_events
from google.adk.tools import ToolContext

@pytest.mark.asyncio
async def test_agent_definition():
    assert root_agent.name == "exec_func_coach"
    assert len(root_agent.tools) >= 1
    tool_names = [t.name if hasattr(t, 'name') else t.__name__ for t in root_agent.tools]
    assert "get_user_calendar_events" in tool_names

@pytest.mark.asyncio
async def test_calendar_tool_no_auth():
    # Test that the tool raises ValueError if no user_id is in state
    tool_context = ToolContext() # Has empty state
    
    result = await get_user_calendar_events(
        start_date="2023-01-01",
        end_date="2023-01-02",
        tool_context=tool_context
    )
    # The tool captures exceptions and returns error dict
    assert result["status"] == "error"
    assert "User ID not found" in result["message"]

@pytest.mark.asyncio
async def test_calendar_tool_mocked_service():
    # Test the tool logic with mocked Google Service
    from unittest.mock import MagicMock, AsyncMock, patch
    
    mock_service = MagicMock()
    mock_events = mock_service.events.return_value.list.return_value.execute.return_value
    mock_events.get.return_value = [
        {
            "id": "1",
            "summary": "Test Event",
            "start": {"dateTime": "2023-01-01T10:00:00Z"},
            "status": "confirmed"
        }
    ]
    
    # Mock the helper that gets credentials and builds service
    with patch("agents.exec_func_coach.tools._get_calendar_service", new_callable=AsyncMock) as mock_get_service:
        mock_get_service.return_value = mock_service
        
        tool_context = ToolContext()
        tool_context.state['user_db_id'] = str(uuid.uuid4())
        
        result = await get_user_calendar_events(
            start_date="2023-01-01",
            end_date="2023-01-02",
            tool_context=tool_context
        )
        
        assert result.get("count") == 1
        assert result["events"][0]["summary"] == "Test Event"
