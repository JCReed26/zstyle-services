"""Main entry point — three agent endpoints + automation scheduler"""

from src.agents import create_exec_func_coach_agent, create_personal_assistant_agent, create_health_agent
from src.scheduler import start_scheduler

exec_func_coach_graph = create_exec_func_coach_agent()
personal_assistant_graph = create_personal_assistant_agent()
health_agent_graph = create_health_agent()

# Start background automations
_scheduler = start_scheduler()
