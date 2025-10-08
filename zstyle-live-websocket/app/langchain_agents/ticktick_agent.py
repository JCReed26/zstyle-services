"""TickTick Agent Toolset"""
import os 
from dotenv import load_dotenv
from datetime import datetime

from langchain_core.tools import tool
from langchain.agents import ToolNode, create_agent

from ticktick.oauth2 import OAuth2
from ticktick.api import TickTickClient

load_dotenv()

_id = os.getenv("TICKTICK_CLIENT_ID") or ""
_secret = os.getenv("TICKTICK_CLIENT_SECRET") or ""
_uri = os.getenv("TICKTICK_REDIRECT_URI") or ""

auth_client = OAuth2(
    client_id=_id,
    client_secret=_secret,
    redirect_uri=_uri,
)

ticktick_username = os.getenv("TICKTICK_USERNAME") or ""
ticktick_password = os.getenv("TICKTICK_PASSWORD") or ""

client = TickTickClient(
    username=ticktick_username, 
    password=ticktick_password, 
    oauth=auth_client,
)

https://lazeroffmichael.github.io/ticktick-py/usage/tasks/
# Example Tasks Dictionary
""" {
    "id": "String",
    "projectId": "String",
    "title": "Task Title",
    "content": "Task Content",
    "desc": "Task Description",
    "allDay": True,
    "startDate": "2019-11-13T03:00:00+0000",
    "dueDate": "2019-11-14T03:00:00+0000",
    "timeZone": "America/Los_Angeles",
    "reminders": ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"],
    "repeat": "RRULE:FREQ=DAILY;INTERVAL=1",
    "priority": 1,
    "status": 0,
    "completedTime": "2019-11-13T03:00:00+0000",
    "sortOrder": 12345,
    "items": [{
        "id": "String",
        "status": 1,
        "title": "Subtask Title",
        "sortOrder": 12345,
        "startDate": "2019-11-13T03:00:00+0000",
        "isAllDay": False,
        "timeZone": "America/Los_Angeles",
        "completedTime": "2019-11-13T03:00:00+0000"
    }],
} """

## Client Tools
@tool
def get_by_id():
    """Get user data by id"""
    user_data = client.get_by_id("1")
    return user_data

@tool
def get_tasks() -> list:
    """Get all tasks"""
    tasks = client.state['tasks']
    return tasks

@tool 
def get_tags() -> list:
    """Get all tags"""
    tags = client.state['tags']
    return tags

@tool
def get_projects() -> list:
    """Get all projects"""
    projects = client.state['projects']
    return projects

## Task Tools
@tool
def build_task(
    title='',
    projectId=None,
    content=None,
    desc=None,
    allDay=None,
    startDate=None,
    dueDate=None,
    timeZone=None,
    reminders=None,
    repeat=None,
    priority=None,
    sortOrder=None,
    items=None
) -> dict:
    """Build a task dictionary for creating or updating a task before passing to create_task or update_task."""
    task = {
        "title": title,
        "projectId": projectId,
        "content": content,
        "desc": desc,
        "allDay": allDay,
        "startDate": startDate,
        "dueDate": dueDate,
        "timeZone": timeZone,
        "reminders": reminders,
        "repeat": repeat,
        "priority": priority,
        "sortOrder": sortOrder,
        "items": items,
    }
    return {k: v for k, v in task.items() if v is not None}

@tool
def complete_task(task: dict) -> dict:
    """Complete a task"""
    completed_task = client.task.complete(task)
    return completed_task

@tool
def create_task(task: dict) -> dict:
    """Create a new task"""
    new_task = client.task.create(task)
    return new_task

@tool 
def dates(start, due=None, tz=None) -> dict:
    """Necessary date conversions from datetime objects to strings to input into task builder(build_task)"""
    dates = client.task.dates(start=start, due=due, tz=tz)
    return dates

@tool
def delete_task(task) -> dict:
    """Delete a task"""
    deleted_task = client.task.delete(task)
    return deleted_task

@tool
def get_completed_tasks(start, end=None, full=True, tz=None) -> list:
    """Get completed tasks within a date range"""
    completed_tasks = client.task.get_completed(start=start, end=end, full=full, tz=tz)
    return completed_tasks

@tool
def get_tasks_from_project(project):
    """Get tasks from a specific project"""
    tasks = client.task.get_from_project(project)
    return tasks # returns dict is single task, list if multiple or none

@tool
def make_subtask(obj, parent):
    """Make the passed task(s) a subtask of the parent task"""
    # all tasks must be fully built/created before calling this function
    subtask = client.task.make_subtask(obj, parent)
    return subtask

@tool
def move_task(obj, new):
    """Move a task to a different project"""
    moved_task = client.task.move(obj, new)
    return moved_task # returns dict if single task, list if multiple

@tool
def move_all_tasks(old, new) -> list:
    """Move all tasks from one project to another"""
    moved_tasks = client.task.move_all(old['id'], new['id'])
    return moved_tasks

@tool
def update_task(task) -> dict:
    """Update a task with the provided updates dictionary"""
    updated_task = client.task.update(task)
    return updated_task

## Handle Error
def handle_errors(e: ValueError) -> str:
    return f"Invalid Input Provided. Error: {str(e)}"

## Agent Toolset
ticktick_tool_node = ToolNode(
    tools=[
        get_by_id,
        get_tasks,
        get_tags,
        get_projects,
        build_task,
        complete_task,
        create_task,
        dates,
        delete_task,
        get_completed_tasks,
        get_tasks_from_project,
        make_subtask,
        move_task,
        move_all_tasks,
        update_task,
    ],
    handle_tool_error=handle_errors,
)

ticktick_agent = create_agent(
    model="gemini-2.5-flash",
    tools=ticktick_tool_node,
    prompt="""You are a helpful AI assistant that can manage tasks using TickTick."""
)