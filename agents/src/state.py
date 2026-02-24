"""Shared AG-UI state schema — each agent owns one slice"""

from typing_extensions import TypedDict
from typing import Optional


# --- Vision Board (exec_func_coach owns) ---
class Goal(TypedDict):
    id: str
    title: str
    description: str
    category: str  # "health", "career", "relationships", etc.
    progress: int  # 0-100


class Habit(TypedDict):
    id: str
    title: str
    frequency: str  # "daily", "weekly"
    streak: int
    completed_today: bool


class VisionBoardState(TypedDict):
    goals: list[Goal]
    habits: list[Habit]
    lifestyle_theme: str


# --- Personal Assistant (personal_assistant owns) ---
class CalendarBlock(TypedDict):
    id: str
    title: str
    start: str  # ISO datetime
    end: str
    type: str  # "work", "health", "personal"


class EmailSummary(TypedDict):
    id: str
    subject: str
    from_address: str
    summary: str
    action_required: bool


class Task(TypedDict):
    id: str
    title: str
    list_name: str
    due: Optional[str]
    completed: bool


class Automation(TypedDict):
    id: str
    name: str
    agent: str  # "personal_assistant" | "health_agent"
    cron: str
    enabled: bool
    last_run: Optional[str]


class PersonalAssistantState(TypedDict):
    calendar: list[CalendarBlock]
    emails: list[EmailSummary]
    tasks: list[Task]
    automations: list[Automation]


# --- Health (health_agent owns) ---
class WorkoutDay(TypedDict):
    day: str
    workout_type: str
    duration_min: int
    notes: str


class StravaStats(TypedDict):
    recent_run_km: float
    recent_ride_km: float
    ytd_run_km: float
    last_synced: str


class MealPlan(TypedDict):
    monday: list[str]
    tuesday: list[str]
    wednesday: list[str]
    thursday: list[str]
    friday: list[str]
    saturday: list[str]
    sunday: list[str]


class HealthState(TypedDict):
    weekly_plan: list[WorkoutDay]
    strava_stats: StravaStats
    meal_plan: MealPlan
    shopping_list: list[str]


# --- Full AG-UI State ---
class ZStyleState(TypedDict):
    vision_board: VisionBoardState
    personal_assistant: PersonalAssistantState
    health: HealthState
