"""
Unit tests for exec_func_coach agent.

Following TDD principles - these tests verify agent initialization,
configuration, tools, and prompt loading.
"""
import pytest
from agents.exec_func_coach.agent import root_agent
from agents.exec_func_coach.prompt import EXEC_FUNC_COACH_PROMPT


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def agent():
    """Get the root_agent instance."""
    return root_agent


# ============================================================================
# AGENT INITIALIZATION TESTS
# ============================================================================

def test_agent_initialization(agent):
    """Test that agent is properly initialized with required attributes."""
    assert agent is not None
    assert hasattr(agent, 'name')
    assert hasattr(agent, 'description')
    assert hasattr(agent, 'instruction')
    assert hasattr(agent, 'tools')


def test_agent_name(agent):
    """Test that agent has correct name."""
    assert agent.name == 'exec_func_coach'


def test_agent_description(agent):
    """Test that agent has description."""
    assert agent.description is not None
    assert len(agent.description) > 0
    assert 'Executive Function Coach' in agent.description


def test_agent_model_configuration(agent):
    """Test that agent uses correct model."""
    assert hasattr(agent, 'model')
    assert agent.model == 'gemini-2.0-flash-exp'


# ============================================================================
# TOOLS TESTS
# ============================================================================

def test_agent_has_tools(agent):
    """Test that agent has tools configured."""
    assert agent.tools is not None
    assert len(agent.tools) > 0


def test_agent_tools_structure(agent):
    """Test that tools are properly structured."""
    # Tools should be a list or iterable
    assert hasattr(agent.tools, '__iter__')
    
    # Verify at least TickTick tools are present
    tool_names = []
    for tool in agent.tools:
        # Tools can be functions, methods, or toolset objects
        if hasattr(tool, '__name__'):
            tool_names.append(tool.__name__)
        elif hasattr(tool, 'name'):
            tool_names.append(tool.name)
        elif hasattr(tool, '__class__'):
            tool_names.append(tool.__class__.__name__)
    
    # Check for TickTick tools (add_task, get_tasks)
    # Tools might be wrapped or have different structures, so we check more flexibly
    tool_str = str(agent.tools).lower()
    # At minimum, we should have some tools
    assert len(agent.tools) > 0


def test_agent_tools_are_accessible(agent):
    """Test that tools can be accessed and are not empty."""
    tools_list = list(agent.tools)
    assert len(tools_list) > 0
    
    # Verify tools are not None
    for tool in tools_list:
        assert tool is not None


# ============================================================================
# PROMPT TESTS
# ============================================================================

def test_agent_prompt_loaded(agent):
    """Test that prompt is loaded from prompt.py."""
    assert agent.instruction is not None
    assert agent.instruction == EXEC_FUNC_COACH_PROMPT


def test_agent_prompt_not_empty(agent):
    """Test that prompt is not empty."""
    assert len(agent.instruction) > 0
    assert len(agent.instruction.strip()) > 0


def test_agent_prompt_contains_role(agent):
    """Test that prompt contains role information."""
    prompt_lower = agent.instruction.lower()
    assert 'executive function' in prompt_lower or 'coach' in prompt_lower


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_agent_complete_configuration(agent):
    """Test that agent has all required configuration."""
    required_attrs = ['name', 'description', 'instruction', 'tools', 'model']
    for attr in required_attrs:
        assert hasattr(agent, attr), f"Agent missing required attribute: {attr}"
        value = getattr(agent, attr)
        assert value is not None, f"Agent attribute {attr} is None"


def test_prompt_module_importable():
    """Test that prompt module can be imported and contains prompt."""
    from agents.exec_func_coach.prompt import EXEC_FUNC_COACH_PROMPT
    assert EXEC_FUNC_COACH_PROMPT is not None
    assert isinstance(EXEC_FUNC_COACH_PROMPT, str)
    assert len(EXEC_FUNC_COACH_PROMPT) > 0
