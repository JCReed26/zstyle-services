import pytest
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext

# We attempt to import the agent. If it fails due to broken dependencies, the test collection will fail, 
# which is a valid TDD red state.
try:
    from agents.exec_func_coach.agent import root_agent
    from agents.exec_func_coach.helpers import get_current_goal
except ImportError:
    root_agent = None
    get_current_goal = None

@pytest.mark.asyncio
async def test_get_current_goal_logic(mock_tool_context):
    """
    Test that get_current_goal calls the memory service correctly.
    """
    if get_current_goal is None:
        pytest.fail("Could not import get_current_goal due to broken dependencies")

    with patch("agents.exec_func_coach.helpers.memory_service") as mock_memory:
        # Mock the memory slot return value
        mock_memory.get_memory_slot = (
            pytest.AsyncMock(return_value={"goal": "Buy milk"}) 
            if hasattr(pytest, 'AsyncMock') 
            else MagicMock(return_value={"goal": "Buy milk"})
        )
        # Ensure it's awaitable if using MagicMock
        if not hasattr(pytest, 'AsyncMock'):
             async def async_return(): return {"goal": "Buy milk"}
             mock_memory.get_memory_slot.return_value = async_return()
             mock_memory.get_memory_slot = MagicMock(side_effect=lambda *args, **kwargs: async_return())

        result = await get_current_goal(mock_tool_context)
        
        assert result["status"] == "success"
        assert result["goal"] == {"goal": "Buy milk"}
        
        # Verify it was called with correct user_id
        args, _ = mock_memory.get_memory_slot.call_args
        assert args[0] == "test-user-123"

def test_agent_tools_configuration():
    """
    Verify the agent has the expected tools registered.
    """
    if root_agent is None:
        pytest.fail("Could not import root_agent due to broken dependencies")

    # Check if get_current_goal is in the tools list
    assert get_current_goal in root_agent.tools, "get_current_goal should be a registered tool"

    # Check for ticktick tool presence
    # We don't know the exact object yet, but we can check the list length or types
    tool_names = [str(t) for t in root_agent.tools]
    assert any("ticktick" in name.lower() for name in tool_names), "TickTick tool should be registered"

