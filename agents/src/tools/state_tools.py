from typing import List, Optional, Any
from langchain.tools import tool
from src.state import Goal, Habit, CalendarBlock, EmailSummary, Task, Automation, WorkoutDay, StravaStats, MealPlan
try:
    from copilotkit.langgraph import copilotkit_emit_state
except ImportError:
    # Fallback or mock for environments where copilotkit is not available
    def copilotkit_emit_state(state: Any):
        pass

# --- Vision Board Tools ---
@tool
def update_vision_board(goals: List[Goal], habits: List[Habit], lifestyle_theme: str = "My Lifestyle"):
    """
    Update the user's vision board (goals, habits, theme).
    Call this tool whenever you need to create, modify, or delete goals/habits or update the theme.
    """
    copilotkit_emit_state({"vision_board": {"goals": goals, "habits": habits, "lifestyle_theme": lifestyle_theme}})
    return "Vision board updated."

# --- Personal Assistant Tools ---
@tool
def update_personal_assistant(
    calendar: Optional[List[CalendarBlock]] = None,
    emails: Optional[List[EmailSummary]] = None,
    tasks: Optional[List[Task]] = None,
    automations: Optional[List[Automation]] = None
):
    """
    Update the personal assistant dashboard state.
    Provide only the fields you want to update (calendar, emails, tasks, automations).
    """
    updates = {}
    if calendar is not None:
        updates["calendar"] = calendar
    if emails is not None:
        updates["emails"] = emails
    if tasks is not None:
        updates["tasks"] = tasks
    if automations is not None:
        updates["automations"] = automations
    
    if updates:
        copilotkit_emit_state({"personal_assistant": updates})
        return "Personal Assistant dashboard updated."
    return "No updates provided."

# --- Health Agent Tools ---
@tool
def update_health(
    weekly_plan: Optional[List[WorkoutDay]] = None,
    strava_stats: Optional[StravaStats] = None,
    meal_plan: Optional[MealPlan] = None,
    shopping_list: Optional[List[str]] = None
):
    """
    Update the health dashboard state.
    Provide only the fields you want to update (weekly_plan, strava_stats, meal_plan, shopping_list).
    """
    updates = {}
    if weekly_plan is not None:
        updates["weekly_plan"] = weekly_plan
    if strava_stats is not None:
        updates["strava_stats"] = strava_stats
    if meal_plan is not None:
        updates["meal_plan"] = meal_plan
    if shopping_list is not None:
        updates["shopping_list"] = shopping_list
        
    if updates:
        copilotkit_emit_state({"health": updates})
        return "Health dashboard updated."
    return "No updates provided."
