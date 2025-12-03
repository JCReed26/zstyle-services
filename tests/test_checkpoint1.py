import pytest
from httpx import AsyncClient, ASGITransport
from main import app  # Import the FastAPI app directly

@pytest.mark.asyncio
async def test_agent_basic_chat():
    """
    Checkpoint 1 Test:
    Verifies that the Agent API endpoint accepts a prompt and session_id,
    and returns a text response.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        agent_name = "exec_func_coach"
        user_id = "test_user_999"
        
        # 1. Create Session
        create_session_url = f"/apps/{agent_name}/users/{user_id}/sessions"
        print(f"Creating session at: {create_session_url}")
        
        session_resp = await ac.post(create_session_url)
        assert session_resp.status_code == 200, f"Create Session failed: {session_resp.text}"
        
        session_data = session_resp.json()
        print(f"Session Created: {session_data}")
        session_id = session_data.get("id")
        assert session_id is not None
        
        # 2. Run Agent
        payload = {
            "appName": agent_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": "Hello, are you there?"}]
            }
        }
        
        url = "/run"
        print(f"Testing URL: {url} with payload: {payload}")
        
        response = await ac.post(url, json=payload)
        
        # Check status
        assert response.status_code == 200, f"Failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Agent Response: {data}")
        
        # Verify response structure (List of events)
        assert isinstance(data, list), "Response should be a list of events"
        
        response_text = ""
        for event in data:
            # Look for model content
            content = event.get("content")
            if content and isinstance(content, dict):
                parts = content.get("parts")
                if parts and isinstance(parts, list):
                    for part in parts:
                        text = part.get("text")
                        if text:
                            response_text += text
                            
        assert len(response_text) > 0, "No text response found in events"
        print(f"Final Response Text: {response_text}")
