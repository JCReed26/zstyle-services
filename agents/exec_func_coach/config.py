from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class AgentConfig(BaseModel):
    name: str
    description: str
    llm_model: str = "gemini-2.5-flash"
    model_params: Dict[str, Any] = {}
    auth_requirements: List[str] = []
    tools_config: Dict[str, Any] = {}
    memory_config: Dict[str, Any] = {}
    runner_type: str = "adk"


# Default configuration for exec_func_coach agent
EXEC_FUNC_COACH_CONFIG = AgentConfig(
    name="exec_func_coach",
    description="Executive Function Personal Life Coach",
    llm_model="gemini-2.5-flash",
    auth_requirements=["ticktick", "google_calendar"],  # Required integrations
    tools_config={
        "calendar": True,
        "task_management": True,
        "reminder_system": True
    },
    memory_config={
        "long_term_memory": True,
        "context_persistence": True
    }
)