import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoint:
    def test_health_returns_200(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestChatEndpoint:
    def test_unknown_agent_returns_404(self, test_client):
        response = test_client.post(
            "/api/v1/chat/unknown_agent",
            json={"user_id": "test", "message": "hello"},
        )
        assert response.status_code == 404

    def test_valid_agent_returns_200(self, test_client):
        with patch("app.agents.exec_func_coach.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "Test response"
            response = test_client.post(
                "/api/v1/chat/exec_func_coach",
                json={"user_id": "test_user", "message": "hello"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "exec_func_coach"
        assert data["response"] == "Test response"

    def test_missing_user_id_returns_422(self, test_client):
        response = test_client.post(
            "/api/v1/chat/exec_func_coach",
            json={"message": "hello"},
        )
        assert response.status_code == 422

    def test_missing_message_returns_422(self, test_client):
        response = test_client.post(
            "/api/v1/chat/exec_func_coach",
            json={"user_id": "test"},
        )
        assert response.status_code == 422

    def test_all_agents_are_routable(self, test_client):
        agents = ["exec_func_coach", "fitness_coach", "nutritionist", "personal_assistant"]
        for agent_name in agents:
            with patch(f"app.agents.{agent_name}.chat", new_callable=AsyncMock) as mock_chat:
                mock_chat.return_value = f"Response from {agent_name}"
                response = test_client.post(
                    f"/api/v1/chat/{agent_name}",
                    json={"user_id": "test", "message": "hi"},
                )
            assert response.status_code == 200, f"Agent {agent_name} failed"
            assert response.json()["agent"] == agent_name
