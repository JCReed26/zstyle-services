try:
    from agents.exec_func_coach.capabilities import google_gmail_tool
    print(f"Tool name: {google_gmail_tool.name}")
    print(f"Tool repr: {google_gmail_tool}")
except Exception as e:
    print(f"Error: {e}")

