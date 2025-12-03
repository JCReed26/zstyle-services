from google.adk.agents import Agent
from google.adk.tools import McpToolset
from mcp import StdioServerParameters
from .tools import (
    get_user_calendar_events,
    add_calendar_event,
    delete_calendar_event,
    create_reminder,
    get_task_list,
    add_task
)

# Configuration for the Telegram MCP Server
# We run the local script as a subprocess
telegram_mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["services/telegram_mcp/main.py"]
    )
)

# Define the executive function coach agent with tools
root_agent = Agent(
    model='gemini-2.5-flash',
    name='exec_func_coach',
    description='Executive Function Personal Life Coach',
    instruction='''
    You are an executive function coach helping users organize their personal life.
    
    You have access to the user's Google Calendar and Telegram (via MCP).
    - Use `get_user_calendar_events` to check their schedule.
    - Use `add_calendar_event` to schedule new appointments.
    - Use `create_reminder` to set quick reminders.
    
    You can also interact with Telegram using the available MCP tools.
    - Use `send_message` to send messages.
    - Use `get_chats` or `list_chats` to see conversations.
    - Use `get_messages` to read history.
    
    When modifying the calendar (adding/removing), always confirm details.
    
    Be helpful, organized, and provide actionable advice.
    ''',
    tools=[
        get_user_calendar_events,
        add_calendar_event,
        delete_calendar_event,
        create_reminder,
        get_task_list,
        add_task,
        telegram_mcp_toolset
    ]
)