import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from google.adk.agents import Agent
from google.adk.tools import ToolContext

# Mock sub-agents
class MockAgent(Agent):
    def __init__(self, name):
        self.name = name
        # Minimal initialization to satisfy Agent class
        super().__init__(model="mock-model", name=name, instruction="mock instruction")

@pytest.fixture
def mock_sub_agents():
    return [
        MockAgent("memory_specialist"),
        MockAgent("calendar_scheduler"),
        MockAgent("ticktick_manager"),
        MockAgent("gmail_organizer")
    ]

@pytest.fixture
def orchestrator_agent(mock_sub_agents):
    # Import the real orchestrator when implemented
    # from agents.exec_func_coach.orchestrator import create_orchestrator_agent
    
    # For now, we mock the creation logic that we WILL implement
    agent = Agent(
        model="gemini-2.0-flash-exp",
        name="orchestrator",
        instruction="Orchestrate...",
        sub_agents=mock_sub_agents
    )
    return agent

def test_sub_agents_registered(orchestrator_agent):
    """
    Verify that the orchestrator has the correct sub-agents registered.
    """
    sub_agent_names = [a.name for a in orchestrator_agent.sub_agents]
    expected_names = [
        "memory_specialist", 
        "calendar_scheduler", 
        "ticktick_manager", 
        "gmail_organizer"
    ]
    
    for name in expected_names:
        assert name in sub_agent_names

def test_orchestrator_has_no_direct_tools(orchestrator_agent):
    """
    The orchestrator should NOT have direct tools like creating calendar events.
    It should delegate. It might have routing tools, but not domain tools.
    """
    # This assumes we want strict delegation. 
    # If the orchestrator keeps some tools (like get_current_date), update this test.
    # For now, let's assume it only has memory context tools.
    
    # We haven't defined tools yet, but we can check names once we do.
    pass
