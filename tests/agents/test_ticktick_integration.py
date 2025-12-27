import pytest
from unittest.mock import MagicMock, patch
from google.adk.tools import ToolContext

# Reuse existing implementation since we already refactored TickTick
try:
    from agents.exec_func_coach.ticktick import ticktick_agent
except ImportError:
    ticktick_agent = None

def test_ticktick_agent_initialization():
    """
    Test that the TickTick agent is initialized correctly.
    """
    if ticktick_agent:
        assert ticktick_agent.name == "ticktick_manager"
        assert len(ticktick_agent.tools) > 0
    else:
        pytest.fail("TickTick agent not imported")

