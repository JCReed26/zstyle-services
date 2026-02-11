import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.nutritionist.state import AgentState
from app.agents.nutritionist.prompts import SYSTEM_PROMPT


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

    def test_system_prompt_mentions_nutrition(self):
        assert "nutri" in SYSTEM_PROMPT.lower() or "meal" in SYSTEM_PROMPT.lower()


class TestGraph:
    def test_retrieve_context(self, mock_memory_manager):
        from app.agents.nutritionist.agent import retrieve_context

        state = {
            "messages": [HumanMessage(content="Plan my meals for the week")],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.nutritionist.agent.memory_manager", mock_memory_manager):
            result = retrieve_context(state)

        assert result["context"] == ["Previous conversation context"]
        mock_memory_manager.get_context.assert_called_once_with("test_user", "Plan my meals for the week")

    def test_generate_response(self, mock_llm):
        from app.agents.nutritionist.agent import generate_response

        state = {
            "messages": [HumanMessage(content="Plan my meals for the week")],
            "user_id": "test_user",
            "context": ["user is vegetarian"],
        }

        with patch("app.agents.nutritionist.agent.llm", mock_llm):
            result = generate_response(state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][-1], AIMessage)

    def test_save_to_memory(self, mock_memory_manager):
        from app.agents.nutritionist.agent import save_to_memory

        state = {
            "messages": [
                HumanMessage(content="Plan my meals for the week"),
                AIMessage(content="Here's your meal plan..."),
            ],
            "user_id": "test_user",
            "context": [],
        }

        with patch("app.agents.nutritionist.agent.memory_manager", mock_memory_manager):
            save_to_memory(state)

        mock_memory_manager.save_interaction.assert_called_once_with(
            "test_user", "Plan my meals for the week", "Here's your meal plan..."
        )


@pytest.mark.llm
class TestLLMSmoke:
    async def test_chat_returns_nonempty_response(self):
        from app.agents.nutritionist import chat
        response = await chat("test_user", "What should I eat for breakfast?")
        assert isinstance(response, str)
        assert len(response) > 0
