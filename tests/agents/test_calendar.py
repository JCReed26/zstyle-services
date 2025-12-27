import pytest
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext

@pytest.fixture
def mock_calendar_toolset():
    with patch("agents.exec_func_coach.calendar.CalendarToolset") as mock:
        yield mock

def test_calendar_agent_initialization():
    """
    Test that the Calendar agent is initialized with the correct toolset.
    """
    try:
        from agents.exec_func_coach.calendar import calendar_agent
        assert calendar_agent.name == "calendar_scheduler"
        assert len(calendar_agent.tools) > 0
    except ImportError:
        pytest.fail("Calendar agent not implemented yet")

