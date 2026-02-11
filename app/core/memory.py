from openmemory import OpenMemory
import os

class MemoryManager:
    def __init__(self):
        self.client = OpenMemory(
            mode="remote",
            url=os.getenv("OPENMEMORY_URL", "http://openmemory:8080")
        )

    def get_context(self, user_id: str, query: str) -> list[str]:
        """Retrieve relevant context from memory for this user's query"""
        try:
            results = self.client.query(query, user_id=user_id, limit=5)
            return [r.get("text", "") for r in results]
        except Exception as e:
            print(f"Memory query error: {e}")
            return []

    def save_interaction(self, user_id: str, message: str, response: str):
        """Save conversation turn to long-term memory"""
        try:
            conversation_text = f"User: {message}\nAssistant: {response}"
            self.client.add(conversation_text, user_id=user_id)
        except Exception as e:
            print(f"Memory save error: {e}")

memory_manager = MemoryManager()