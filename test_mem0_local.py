from mem0 import Memory
import os

# Set empty key to simulate docker env
os.environ["OPENAI_API_KEY"] = ""

try:
    print("Initializing Memory...")
    # Try to initialize with default settings (which might fail if it defaults to OpenAI)
    m = Memory()
    print("Memory initialized.")
    m.add("I like coding", user_id="test_user")
    print("Memory added.")
    print(m.search("coding", user_id="test_user"))
except Exception as e:
    print(f"Error: {e}")

