"""Main entry point - two separate agent endpoints"""

from src.agents import create_exec_func_coach_agent, create_personal_assistant_agent

# Two separate endpoints
exec_func_coach_graph = create_exec_func_coach_agent()
personal_assistant_graph = create_personal_assistant_agent()
