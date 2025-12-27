import pytest
import contextvars
from unittest.mock import MagicMock, patch, AsyncMock
from database.models import CredentialType

# Handle imports safely
try:
    from agents.exec_func_coach.ticktick import (
        TickTickAgentTool, 
        DynamicAuthHeaders, 
        _current_ticktick_token,
        ticktick_agent
    )
except ImportError:
    TickTickAgentTool = None
    DynamicAuthHeaders = None

@pytest.mark.asyncio
async def test_dynamic_auth_headers_injection():
    """
    Test that DynamicAuthHeaders injects the token from the context var.
    """
    if DynamicAuthHeaders is None:
        pytest.fail("DynamicAuthHeaders not imported")

    headers = DynamicAuthHeaders()
    
    # 1. No token set
    token = _current_ticktick_token.set(None)
    try:
        assert headers.get("Authorization") == "" or headers.get("Authorization") is None
    finally:
        _current_ticktick_token.reset(token)
        
    # 2. Token set
    token = _current_ticktick_token.set("fake-token-123")
    try:
        assert headers["Authorization"] == "Bearer fake-token-123"
        
        # Verify iteration includes Authorization
        assert "Authorization" in list(headers)
    finally:
        _current_ticktick_token.reset(token)

@pytest.mark.asyncio
async def test_ticktick_agent_tool_execution(mock_tool_context):
    """
    Test that TickTickAgentTool sets the context var during execution.
    """
    if TickTickAgentTool is None:
        pytest.fail("TickTickAgentTool not imported")

    # Mock the _get_credential helper
    with patch("agents.exec_func_coach.ticktick._get_credential") as mock_get_cred:
        mock_get_cred.return_value = {"token": "access-token-xyz"}
        
        # Create the tool wrapper
        tool_wrapper = TickTickAgentTool(agent=ticktick_agent)
        
        # Mock the super().execute method to verify context var state
        # We need to mock super() call which is tricky. 
        # Easier to mock the agent execution or check the context var inside a mocked method.
        
        async def mock_super_execute(self, context, **kwargs):
            # Check if token is set inside the execution scope
            current_token = _current_ticktick_token.get()
            return {"status": "success", "token_seen": current_token}
        
        # Patching AgentTool.execute is hard because it's a class method on the parent.
        # But we can patch the super() call? No.
        # We can assign the method to the instance? No, super() looks at class.
        # We can patch `AgentTool.execute` globally.
        with patch("google.adk.tools.agent_tool.AgentTool.run_async", new=mock_super_execute):
            result = await tool_wrapper.run_async(mock_tool_context)
            
            assert result["status"] == "success"
            assert result["token_seen"] == "access-token-xyz"
        
        # Verify credential was fetched with correct user_id
        mock_get_cred.assert_called_once_with("test-user-123", CredentialType.TICKTICK_TOKEN)
        
        # Verify token is reset after execution
        assert _current_ticktick_token.get() is None

