import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.personal_assistant.state import AgentState
from app.agents.personal_assistant.prompts import SYSTEM_PROMPT


class TestState:
    def test_agent_state_has_required_fields(self):
        state: AgentState = {
            "messages": [],
            "user_id": "test_user",
            "context": [],
        }
        assert "messages" in state
        assert "user_id" in state
        assert "context" in state


class TestPrompts:
    def test_system_prompt_has_context_placeholder(self):
        assert "{context}" in SYSTEM_PROMPT

    def test_system_prompt_formats_correctly(self):
        formatted = SYSTEM_PROMPT.format(context="some context")
        assert "some context" in formatted
        assert "{context}" not in formatted

    def test_system_prompt_mentions_assistant_tasks(self):
        prompt_lower = SYSTEM_PROMPT.lower()
        assert "email" in prompt_lower or "calendar" in prompt_lower or "task" in prompt_lower


class TestGraph:
    def test_retrieve_context(self, mock_memory_manager):
        from app.agents.personal_assistant.agent import retrieve_context

        state = {
            "messages": [HumanMessage(content="Check my email")],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.personal_assistant.agent.memory_manager", mock_memory_manager):
            result = retrieve_context(state)

        assert result["context"] == ["Previous conversation context"]
        mock_memory_manager.get_context.assert_called_once_with("test_user", "Check my email")

    def test_generate_response(self, mock_llm):
        from app.agents.personal_assistant.agent import generate_response

        state = {
            "messages": [HumanMessage(content="Check my email")],
            "user_id": "test_user",
            "context": ["user prefers morning email summaries"],
        }

        with patch("app.agents.personal_assistant.agent.llm_with_tools", mock_llm):
            result = generate_response(state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][-1], AIMessage)

    def test_save_to_memory(self, mock_memory_manager):
        from app.agents.personal_assistant.agent import save_to_memory

        state = {
            "messages": [
                HumanMessage(content="Check my email"),
                AIMessage(content="You have 3 new emails..."),
            ],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.personal_assistant.agent.memory_manager", mock_memory_manager):
            save_to_memory(state)

        mock_memory_manager.save_interaction.assert_called_once_with(
            "test_user", "Check my email", "You have 3 new emails..."
        )


class TestTools:
    def test_tools_load_gracefully_without_credentials(self):
        """Tools should return empty list when Gmail credentials aren't available."""
        from app.agents.personal_assistant.tools import tools
        assert isinstance(tools, list)


@pytest.mark.llm
class TestLLMSmoke:
    async def test_chat_returns_nonempty_response(self):
        from app.agents.personal_assistant import chat
        response = await chat("test_user", "Summarize my inbox")
        assert isinstance(response, str)
        assert len(response) > 0
