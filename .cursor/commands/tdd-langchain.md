---
name: tdd-langchain
description: Test-driven development workflow specifically for LangChain agents. Follows TDD principles: find tests, run to confirm failure, implement incrementally, refactor.
---

# TDD LangChain Workflow

## Overview

This workflow implements Test-Driven Development (TDD) specifically for LangChain agent development. Follow these steps rigorously.

## Workflow Steps

### 1. Find Existing Tests

**Before writing any code**, search for existing tests:

```bash
# Search for test files
find tests/ -name "*test*agent*.py" -o -name "*test*langchain*.py"
grep -r "test.*agent" tests/
```

**Action**: Read existing test files to understand:
- What's already tested
- Test patterns used
- Mock strategies for LLMs

### 2. Run Tests to Confirm Failure (Red)

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agent.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Expected**: Tests should fail (or not exist yet). This confirms we're starting from a known state.

### 3. Write Test First

Create or update test file with the test for your feature:

```python
# tests/test_agent.py
import pytest
from unittest.mock import Mock, patch
from langchain.agents import create_agent

@pytest.mark.asyncio
async def test_agent_processes_user_request():
    """Test that agent can process a user request."""
    # Mock LLM
    mock_llm = Mock()
    mock_llm.invoke.return_value = {"content": "Processed request"}
    
    # Create agent
    agent = create_agent(
        model=mock_llm,
        tools=[],
        system_prompt="Test agent"
    )
    
    # Test
    result = await agent.invoke({
        "messages": [{"role": "user", "content": "test request"}]
    })
    
    # Assert
    assert result is not None
    assert "content" in result
```

### 4. Run Test to Confirm Failure

```bash
pytest tests/test_agent.py::test_agent_processes_user_request -v
```

**Expected**: Test fails because implementation doesn't exist yet.

### 5. Implement Minimum Code to Pass (Green)

Implement the minimal code needed to pass the test:

```python
# app/agents/user_agent.py
from langchain.agents import create_agent

async def create_user_agent():
    """Create a user agent."""
    agent = create_agent(
        model="claude-sonnet-4-20250514",
        tools=[],
        system_prompt="You are a helpful assistant"
    )
    return agent

async def process_request(agent, request: str):
    """Process a user request."""
    result = await agent.invoke({
        "messages": [{"role": "user", "content": request}]
    })
    return result
```

### 6. Run Test Again

```bash
pytest tests/test_agent.py::test_agent_processes_user_request -v
```

**Expected**: Test passes (green).

### 7. Refactor While Keeping Tests Green

Now refactor the code for better design:

- Extract helper functions
- Improve naming
- Add error handling
- Optimize performance

**Important**: After each refactor, run tests to ensure they still pass.

### 8. Add Error Case Tests

Write tests for error scenarios:

```python
@pytest.mark.asyncio
async def test_agent_handles_invalid_input():
    """Test that agent handles invalid input gracefully."""
    agent = await create_user_agent()
    
    with pytest.raises(ValueError):
        await process_request(agent, None)
```

### 9. Implement Error Handling

Add error handling to pass error tests:

```python
async def process_request(agent, request: str):
    """Process a user request with error handling."""
    if not request:
        raise ValueError("Request cannot be empty")
    
    try:
        result = await agent.invoke({
            "messages": [{"role": "user", "content": request}]
        })
        return result
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise
```

## LangChain-Specific Testing Patterns

### Mocking LLM Calls

```python
from unittest.mock import Mock, patch
from langchain_anthropic import ChatAnthropic

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    with patch('langchain_anthropic.ChatAnthropic') as mock:
        mock_instance = Mock()
        mock_instance.invoke.return_value = Mock(content="Test response")
        mock.return_value = mock_instance
        yield mock_instance
```

### Testing Tools

```python
def test_tool_execution():
    """Test that tools are called correctly."""
    def mock_tool(query: str) -> str:
        return f"Result for {query}"
    
    agent = create_agent(
        model=mock_llm,
        tools=[mock_tool],
        system_prompt="Test"
    )
    
    # Test tool usage
    result = agent.invoke({
        "messages": [{"role": "user", "content": "Use tool with query"}]
    })
    
    assert mock_tool.called
```

### Testing LangGraph State Transitions

```python
@pytest.mark.asyncio
async def test_state_transition():
    """Test LangGraph state transitions."""
    from langgraph.graph import StateGraph
    
    graph = create_agent_graph()
    initial_state = {"user_id": "123", "request": "test"}
    
    result = await graph.ainvoke(initial_state)
    
    assert "result" in result
    assert result["result"] is not None
```

## Checklist

Before considering a feature complete:

- [ ] All tests pass
- [ ] Tests cover happy path
- [ ] Tests cover error cases
- [ ] Tests cover edge cases
- [ ] Code is refactored and clean
- [ ] No test warnings or errors
- [ ] Coverage meets project standards

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_agent.py::test_agent_processes_user_request

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run in watch mode (if available)
pytest-watch
```

## Best Practices

1. **One test per behavior**: Each test should verify one specific behavior
2. **Descriptive names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock external dependencies**: Mock LLM calls, API calls, etc.
5. **Fast tests**: Keep tests fast, use mocks for slow operations
6. **Independent tests**: Tests should not depend on each other
