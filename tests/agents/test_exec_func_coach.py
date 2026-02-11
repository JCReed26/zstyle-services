import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.exec_func_coach.state import AgentState
from app.agents.exec_func_coach.prompts import SYSTEM_PROMPT


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


class TestGraph:
    def test_retrieve_context(self, mock_memory_manager):
        from app.agents.exec_func_coach.agent import retrieve_context

        state = {
            "messages": [HumanMessage(content="Help me plan my day")],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.exec_func_coach.agent.memory_manager", mock_memory_manager):
            result = retrieve_context(state)

        assert result["context"] == ["Previous conversation context"]
        mock_memory_manager.get_context.assert_called_once_with("test_user", "Help me plan my day")

    def test_generate_response(self, mock_llm):
        from app.agents.exec_func_coach.agent import generate_response

        state = {
            "messages": [HumanMessage(content="Help me plan my day")],
            "user_id": "test_user",
            "context": ["some prior context"],
        }

        with patch("app.agents.exec_func_coach.agent.llm", mock_llm):
            result = generate_response(state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][-1], AIMessage)
        mock_llm.invoke.assert_called_once()

    def test_save_to_memory(self, mock_memory_manager):
        from app.agents.exec_func_coach.agent import save_to_memory

        state = {
            "messages": [
                HumanMessage(content="Help me plan my day"),
                AIMessage(content="Here's your plan..."),
            ],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.exec_func_coach.agent.memory_manager", mock_memory_manager):
            save_to_memory(state)

        mock_memory_manager.save_interaction.assert_called_once_with(
            "test_user", "Help me plan my day", "Here's your plan..."
        )


@pytest.mark.llm
class TestLLMSmoke:
    async def test_chat_returns_nonempty_response(self):
        from app.agents.exec_func_coach import chat
        response = await chat("test_user", "What should I focus on today?")
        assert isinstance(response, str)
        assert len(response) > 0
