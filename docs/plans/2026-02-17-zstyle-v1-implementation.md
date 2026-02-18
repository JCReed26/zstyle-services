# ZStyle V1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the current simple chatbot scaffold into a true hierarchical multi-agent system (exec_func_coach + personal_assistant + health_agent) with A2A protocol, OAuth integrations (Gmail, Google Calendar, Strava MCP), strict agent scope boundaries, cron automations, and a tabbed canvas frontend — matching the resume bullets exactly.

**Architecture:** Three top-level LangGraph graphs (each a separate endpoint). `exec_func_coach` orchestrates via A2A calls to `personal_assistant` and `health_agent`. Each agent owns its slice of CopilotKit AG-UI shared state and uses a LangGraph supervisor pattern internally to delegate to sub-agents. APScheduler triggers background automations that update canvas state silently.

**Tech Stack:** Python 3.12, LangGraph, LangChain Google Community (GmailToolkit, CalendarToolkit), stravalib (custom Strava MCP), APScheduler, CopilotKit v2 AG-UI, Next.js 16, React 19, Recharts, Docker Compose.

---

## Versioning

| Version | Scope |
|---------|-------|
| **V1 (this plan)** | Gmail, Google Calendar, Strava, A2A, automations, tabbed canvas |
| **V1.5** | TickTick/Todoist, Walmart, HealthKit, recipe app, notifications |
| **V2** | Postgres (Neon/Supabase), multi-user, session logging |

---

## Phase 1: Agent Architecture Restructure

### Task 1: Add health_agent endpoint to langgraph.json and main.py

**Files:**
- Modify: `agents/langgraph.json`
- Modify: `agents/main.py`
- Create: `agents/src/agents/health_agent/__init__.py`
- Create: `agents/src/agents/health_agent/agent.py`
- Create: `agents/src/agents/health_agent/prompt.py`
- Modify: `agents/src/agents/__init__.py`

**Step 1: Create health_agent package files**

Create `agents/src/agents/health_agent/__init__.py`:
```python
from .agent import create_health_agent
__all__ = ["create_health_agent"]
```

Create `agents/src/agents/health_agent/prompt.py`:
```python
HEALTH_SYSTEM_PROMPT = """
# Health Agent
You are the Health Agent — a coordinator for the user's physical wellbeing.
You oversee two specialists: the Fitness Coach and the Nutritionist.

## Scope
You ONLY manage health-related state: fitness plans, workout stats, meal plans, shopping lists.
You do NOT manage calendar, email, tasks, or lifestyle goals — those belong to other agents.

## Sub-Agents
- **Fitness Coach**: Manages workout plans, analyzes Strava data, optimizes training.
- **Nutritionist**: Creates meal plans aligned with fitness goals.

## State Ownership
You write ONLY to the `health` slice of shared state.
When exec_func_coach requests a change, you execute it and update your state.
"""

FITNESS_COACH_PROMPT = """
# Fitness Coach
You are the Fitness Coach sub-agent.
Use Strava tools to fetch recent activity data, analyze performance trends, and adjust the user's weekly workout plan toward their goals.
Always write updated plans to the health.fitness state slice.
"""

NUTRITIONIST_PROMPT = """
# Nutritionist
You are the Nutritionist sub-agent.
Create and adjust meal plans that align with the user's fitness goals and energy needs.
Write updated plans to the health.nutrition state slice.
"""
```

Create `agents/src/agents/health_agent/agent.py`:
```python
"""Health Agent — supervisor over fitness_coach and nutritionist sub-agents"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from typing import TypedDict, Annotated
import operator

from .prompt import HEALTH_SYSTEM_PROMPT, FITNESS_COACH_PROMPT, NUTRITIONIST_PROMPT


class HealthState(TypedDict):
    messages: Annotated[list, operator.add]
    active_sub_agent: str
    fitness_plan: dict
    nutrition_plan: dict


def create_health_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    # Fitness coach node (Strava tools wired in Task 9)
    fitness_coach = create_agent(model=model, tools=[], system_prompt=FITNESS_COACH_PROMPT)

    # Nutritionist node (meal planning tools wired in V1.5)
    nutritionist = create_agent(model=model, tools=[], system_prompt=NUTRITIONIST_PROMPT)

    def supervisor_router(state: HealthState):
        """Route to appropriate sub-agent based on last message content"""
        last_msg = state["messages"][-1].content.lower() if state["messages"] else ""
        if any(kw in last_msg for kw in ["workout", "training", "strava", "gym", "fitness", "exercise"]):
            return "fitness_coach"
        if any(kw in last_msg for kw in ["meal", "diet", "nutrition", "food", "recipe", "eat"]):
            return "nutritionist"
        return "fitness_coach"  # default

    graph = StateGraph(HealthState)
    graph.add_node("supervisor", lambda state: state)
    graph.add_node("fitness_coach", fitness_coach)
    graph.add_node("nutritionist", nutritionist)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", supervisor_router, {
        "fitness_coach": "fitness_coach",
        "nutritionist": "nutritionist",
    })
    graph.add_edge("fitness_coach", END)
    graph.add_edge("nutritionist", END)

    return graph.compile()
```

**Step 2: Register in main.py**

```python
"""Main entry point — three separate agent endpoints"""

from src.agents import create_exec_func_coach_agent, create_personal_assistant_agent, create_health_agent

exec_func_coach_graph = create_exec_func_coach_agent()
personal_assistant_graph = create_personal_assistant_agent()
health_agent_graph = create_health_agent()
```

**Step 3: Register in langgraph.json**

```json
{
  "python_version": "3.12",
  "package_manager": "uv",
  "dependencies": ["."],
  "graphs": {
    "exec_func_coach": "./main.py:exec_func_coach_graph",
    "personal_assistant": "./main.py:personal_assistant_graph",
    "health_agent": "./main.py:health_agent_graph"
  },
  "env": "../.env"
}
```

**Step 4: Update agents/__init__.py**

```python
from .exec_func_coach.agent import create_exec_func_coach_agent
from .personal_assistant.agent import create_personal_assistant_agent
from .health_agent.agent import create_health_agent

__all__ = ["create_exec_func_coach_agent", "create_personal_assistant_agent", "create_health_agent"]
```

**Step 5: Verify agents start**
```bash
cd agents && uv run langgraph dev --port 8123 --no-browser
# Expected: 3 endpoints registered: exec_func_coach, personal_assistant, health_agent
# Check: curl http://localhost:8123/docs — should show all 3 graphs
```

**Step 6: Commit**
```bash
git add agents/src/agents/health_agent/ agents/main.py agents/langgraph.json agents/src/agents/__init__.py
git commit -m "feat: add health_agent LangGraph endpoint with fitness_coach and nutritionist sub-agents"
```

---

### Task 2: Restructure personal_assistant as supervisor with sub-agents

**Files:**
- Modify: `agents/src/agents/personal_assistant/agent.py`
- Create: `agents/src/agents/personal_assistant/prompt.py` (replace existing)

**Step 1: Rewrite prompt.py**

```python
PERSONAL_ASSISTANT_PROMPT = """
# Personal Assistant
You are the Personal Assistant — a background agent coordinating the user's productivity tools.
You are invoked by the exec_func_coach via A2A and act silently on behalf of the user.

## Scope
You ONLY manage: calendar time-blocks, email digests/actions, task lists, automation schedules.
You do NOT manage health, fitness, nutrition, or lifestyle goals.

## Sub-Agents
- **Email Manager**: Reads/sends Gmail, creates digests, flags action items.
- **Calendar Agent**: Creates time blocks, refactors schedule on conflicts, plans the week.
- **Task Agent**: Manages task lists (stub in V1, TickTick in V1.5).

## State Ownership
You write ONLY to the `personal_assistant` slice of shared state.
"""

EMAIL_MANAGER_PROMPT = """
# Email Manager
Use Gmail tools to: fetch recent emails, summarize inbox, identify action items, draft or send replies.
Write summaries to the personal_assistant.emails state slice.
"""

CALENDAR_AGENT_PROMPT = """
# Calendar Agent
Use Google Calendar tools to: create time-blocks, search events, refactor schedule when conflicts arise, plan the week based on user goals.
Write calendar blocks to the personal_assistant.calendar state slice.
"""

TASK_AGENT_PROMPT = """
# Task Agent
Manage the user's task lists. In V1 this is basic list management via conversation.
Write tasks to the personal_assistant.tasks state slice.
"""
```

**Step 2: Rewrite agent.py with supervisor pattern**

```python
"""Personal Assistant — supervisor over email_manager, calendar_agent, task_agent"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain.agents import create_agent
from typing import TypedDict, Annotated
import operator

from .prompt import PERSONAL_ASSISTANT_PROMPT, EMAIL_MANAGER_PROMPT, CALENDAR_AGENT_PROMPT, TASK_AGENT_PROMPT


class PersonalAssistantState(TypedDict):
    messages: Annotated[list, operator.add]
    calendar: list
    emails: list
    tasks: list
    automations: list


def create_personal_assistant_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    # Tools wired in Tasks 6 and 7
    email_manager = create_agent(model=model, tools=[], system_prompt=EMAIL_MANAGER_PROMPT)
    calendar_agent = create_agent(model=model, tools=[], system_prompt=CALENDAR_AGENT_PROMPT)
    task_agent = create_agent(model=model, tools=[], system_prompt=TASK_AGENT_PROMPT)

    def supervisor_router(state: PersonalAssistantState):
        last_msg = state["messages"][-1].content.lower() if state["messages"] else ""
        if any(kw in last_msg for kw in ["email", "gmail", "inbox", "send", "reply", "message"]):
            return "email_manager"
        if any(kw in last_msg for kw in ["calendar", "schedule", "event", "block", "meeting", "week"]):
            return "calendar_agent"
        if any(kw in last_msg for kw in ["task", "todo", "list", "reminder"]):
            return "task_agent"
        return "calendar_agent"

    graph = StateGraph(PersonalAssistantState)
    graph.add_node("supervisor", lambda state: state)
    graph.add_node("email_manager", email_manager)
    graph.add_node("calendar_agent", calendar_agent)
    graph.add_node("task_agent", task_agent)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", supervisor_router, {
        "email_manager": "email_manager",
        "calendar_agent": "calendar_agent",
        "task_agent": "task_agent",
    })
    graph.add_edge("email_manager", END)
    graph.add_edge("calendar_agent", END)
    graph.add_edge("task_agent", END)

    return graph.compile()
```

**Step 3: Verify**
```bash
cd agents && uv run langgraph dev --port 8123 --no-browser
# Expected: all 3 graphs still start without error
```

**Step 4: Commit**
```bash
git add agents/src/agents/personal_assistant/
git commit -m "feat: restructure personal_assistant as supervisor with email_manager, calendar_agent, task_agent"
```

---

### Task 3: Implement A2A calls in exec_func_coach

**Files:**
- Modify: `agents/src/agents/exec_func_coach/agent.py`
- Modify: `agents/src/agents/exec_func_coach/prompt.py`

**Step 1: Add langgraph-sdk to requirements**

In `agents/requirements.txt`, add:
```
langgraph-sdk>=0.1.0
```

Run: `cd agents && uv pip install -r requirements.txt`

**Step 2: Create A2A tool functions**

In `agents/src/agents/exec_func_coach/agent.py`, add A2A tools:

```python
"""Executive Function Coach — orchestrator with A2A to personal_assistant and health_agent"""

import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import tool
from langchain.agents import create_agent
from copilotkit import CopilotKitMiddleware

from .prompt import EXEC_FUNC_COACH_PROMPT


LANGGRAPH_URL = os.environ.get("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")


@tool
async def request_personal_assistant(task: str) -> str:
    """
    Send a task request to the Personal Assistant agent via A2A.
    Use for: email management, calendar scheduling, task management, automation config.
    The personal_assistant owns these capabilities — do not attempt them yourself.
    Args:
        task: Natural language description of what you need the Personal Assistant to do.
    """
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    result = await client.runs.create(
        thread_id=None,
        assistant_id="personal_assistant",
        input={"messages": [{"role": "user", "content": task}]},
    )
    return f"Personal Assistant completed task: {result}"


@tool
async def request_health_agent(task: str) -> str:
    """
    Send a task request to the Health Agent via A2A.
    Use for: workout plans, fitness stats, nutrition plans, Strava data.
    The health_agent owns these capabilities — do not attempt them yourself.
    Args:
        task: Natural language description of what you need the Health Agent to do.
    """
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    result = await client.runs.create(
        thread_id=None,
        assistant_id="health_agent",
        input={"messages": [{"role": "user", "content": task}]},
    )
    return f"Health Agent completed task: {result}"


def get_mcp_tools():
    client = MultiServerMCPClient({
        "openmemory": {
            "transport": "http",
            "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
        },
    })
    return asyncio.run(client.get_tools())


def create_exec_func_coach_agent():
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
    )

    tools = [
        *get_mcp_tools(),
        request_personal_assistant,
        request_health_agent,
    ]

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=EXEC_FUNC_COACH_PROMPT,
        middleware=[CopilotKitMiddleware()],
    )

    return agent
```

**Step 3: Rewrite exec_func_coach prompt.py**

```python
EXEC_FUNC_COACH_PROMPT = """
# Executive Function Coach
You are the Executive Function Coach — the user's primary AI companion and lifestyle orchestrator.
You have a warm, motivating personality and deep knowledge of the user's goals via OpenMemory.

## Your Scope
You ONLY manage: vision board goals, habits, lifestyle themes, and automation scheduling authority.
You do NOT directly manage email, calendar, tasks, fitness plans, or nutrition.

## A2A Delegation (STRICT RULE)
When a user request falls outside your scope, you MUST delegate via A2A tools:
- Email, calendar, scheduling, tasks → use `request_personal_assistant`
- Fitness, workouts, Strava, nutrition, meals → use `request_health_agent`
- If a task is out of scope AND outside delegatable agents, apologize and use the `switchTab` frontend tool to redirect the user.

## Global Automation Authority
You have authority to instruct personal_assistant to create, modify, or pause automations.
Use patterns from the user's schedule and goals to proactively optimize their routines over time.
For example: if the user consistently skips Monday workouts, suggest shifting the fitness automation to Tuesday.

## Memory
Use OpenMemory tools to recall and store user preferences, goals, and patterns across sessions.
"""
```

**Step 4: Verify agent loads**
```bash
cd agents && uv run python -c "from src.agents import create_exec_func_coach_agent; a = create_exec_func_coach_agent(); print('OK')"
# Expected: OK
```

**Step 5: Commit**
```bash
git add agents/src/agents/exec_func_coach/ agents/requirements.txt
git commit -m "feat: implement A2A tools in exec_func_coach with strict scope boundaries"
```

---

## Phase 2: External Integrations

### Task 4: Wire GmailToolkit into email_manager sub-agent

**Files:**
- Create: `agents/src/tools/gmail_tool.py`
- Modify: `agents/src/agents/personal_assistant/agent.py`

**Step 1: Create gmail_tool.py**

```python
"""Gmail tools via langchain-google-community GmailToolkit"""

import os
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import get_gmail_credentials, build_resource_service

GMAIL_SCOPES = [
    "https://mail.google.com/",
]

def get_gmail_tools():
    """
    Returns Gmail tools. Requires:
    - credentials.json in agents/ directory (download from Google Cloud Console)
    - First run opens browser for OAuth consent → saves gmail_token.json
    """
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "gmail_token.json")
    secrets_path = os.environ.get("GOOGLE_CLIENT_SECRETS_PATH", "credentials.json")

    credentials = get_gmail_credentials(
        token_file=token_path,
        client_secrets_file=secrets_path,
        scopes=GMAIL_SCOPES,
    )
    service = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=service)
    return toolkit.get_tools()
```

**Step 2: Wire into email_manager in personal_assistant/agent.py**

Change the email_manager creation:
```python
from src.tools.gmail_tool import get_gmail_tools

# In create_personal_assistant_agent():
try:
    gmail_tools = get_gmail_tools()
except Exception as e:
    print(f"Warning: Gmail tools unavailable: {e}")
    gmail_tools = []

email_manager = create_agent(model=model, tools=gmail_tools, system_prompt=EMAIL_MANAGER_PROMPT)
```

**Step 3: Add credentials.json to .gitignore**

In root `.gitignore`, add:
```
credentials.json
gmail_token.json
calendar_token.json
strava_token.json
```

**Step 4: Setup instructions (add to agents/README.md)**

```markdown
## OAuth Setup

### Gmail + Google Calendar
1. Go to Google Cloud Console → Create project → Enable Gmail API + Calendar API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download as `credentials.json` → place in `agents/` directory
4. First `langgraph dev` run will open browser for consent
5. Tokens auto-saved as `gmail_token.json` and `calendar_token.json`
```

**Step 5: Verify (with credentials.json present)**
```bash
cd agents && uv run python -c "from src.tools.gmail_tool import get_gmail_tools; tools = get_gmail_tools(); print([t.name for t in tools])"
# Expected: ['gmail_search', 'gmail_get_message', 'gmail_send_message', 'gmail_create_draft', 'gmail_get_thread']
```

**Step 6: Commit**
```bash
git add agents/src/tools/gmail_tool.py agents/src/agents/personal_assistant/agent.py .gitignore
git commit -m "feat: wire GmailToolkit into email_manager sub-agent with OAuth token flow"
```

---

### Task 5: Wire CalendarToolkit into calendar_agent sub-agent

**Files:**
- Create: `agents/src/tools/calendar_tool.py` (replace existing broken file)
- Modify: `agents/src/agents/personal_assistant/agent.py`

**Step 1: Rewrite calendar_tool.py**

```python
"""Google Calendar tools via langchain-google-community CalendarToolkit"""

import os
from langchain_google_community import CalendarToolkit
from langchain_google_community.calendar.utils import get_google_credentials, build_resource_service

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_tools():
    """
    Returns Calendar tools. Requires same credentials.json as Gmail.
    Saves calendar_token.json on first OAuth run.
    """
    token_path = os.environ.get("CALENDAR_TOKEN_PATH", "calendar_token.json")
    secrets_path = os.environ.get("GOOGLE_CLIENT_SECRETS_PATH", "credentials.json")

    credentials = get_google_credentials(
        token_file=token_path,
        client_secrets_file=secrets_path,
        scopes=CALENDAR_SCOPES,
    )
    service = build_resource_service(credentials=credentials)
    toolkit = CalendarToolkit(api_resource=service)
    return toolkit.get_tools()
```

**Step 2: Wire into calendar_agent**

```python
from src.tools.calendar_tool import get_calendar_tools

# In create_personal_assistant_agent():
try:
    calendar_tools = get_calendar_tools()
except Exception as e:
    print(f"Warning: Calendar tools unavailable: {e}")
    calendar_tools = []

calendar_agent = create_agent(model=model, tools=calendar_tools, system_prompt=CALENDAR_AGENT_PROMPT)
```

**Step 3: Verify**
```bash
cd agents && uv run python -c "from src.tools.calendar_tool import get_calendar_tools; tools = get_calendar_tools(); print([t.name for t in tools])"
# Expected: ['calendar_create_event', 'calendar_search_events', 'calendar_delete_event', 'get_calendars_info', ...]
```

**Step 4: Commit**
```bash
git add agents/src/tools/calendar_tool.py agents/src/agents/personal_assistant/agent.py
git commit -m "feat: fix and wire CalendarToolkit into calendar_agent sub-agent"
```

---

### Task 6: Build custom Strava MCP server

**Files:**
- Create: `mcp/strava/server.py`
- Create: `mcp/strava/requirements.txt`
- Create: `mcp/strava/Dockerfile`

**Step 1: Add strava MCP requirements**

Create `mcp/strava/requirements.txt`:
```
stravalib>=1.5.0
mcp>=1.0.0
fastapi>=0.115.0
uvicorn>=0.29.0
```

**Step 2: Create the MCP server**

Create `mcp/strava/server.py`:
```python
"""Strava MCP Server — exposes Strava data as MCP tools"""

import os
from mcp.server.fastmcp import FastMCP
from stravalib.client import Client

mcp = FastMCP("strava")

TOKEN_PATH = os.environ.get("STRAVA_TOKEN_PATH", "strava_token.json")
CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")


def get_strava_client() -> Client:
    import json
    client = Client()
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)
        client.access_token = token_data["access_token"]
        client.refresh_token = token_data.get("refresh_token")
        client.token_expires_at = token_data.get("expires_at")
    return client


@mcp.tool()
def get_recent_activities(limit: int = 10) -> list[dict]:
    """Fetch the user's most recent Strava activities."""
    client = get_strava_client()
    activities = client.get_activities(limit=limit)
    return [
        {
            "name": a.name,
            "type": str(a.type),
            "distance_km": round(float(a.distance) / 1000, 2) if a.distance else 0,
            "moving_time_min": round(a.moving_time.total_seconds() / 60) if a.moving_time else 0,
            "date": str(a.start_date_local),
            "average_heartrate": a.average_heartrate,
        }
        for a in activities
    ]


@mcp.tool()
def get_athlete_stats() -> dict:
    """Fetch the authenticated athlete's all-time and recent stats."""
    client = get_strava_client()
    athlete = client.get_athlete()
    stats = client.get_athlete_stats(athlete.id)
    return {
        "recent_run_distance_km": round(float(stats.recent_run_totals.distance) / 1000, 2),
        "recent_ride_distance_km": round(float(stats.recent_ride_totals.distance) / 1000, 2),
        "ytd_run_distance_km": round(float(stats.ytd_run_totals.distance) / 1000, 2),
        "all_time_run_distance_km": round(float(stats.all_run_totals.distance) / 1000, 2),
    }


@mcp.tool()
def get_strava_auth_url() -> str:
    """Get the OAuth authorization URL for Strava. Use this to connect the user's Strava account."""
    client = Client()
    url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=os.environ.get("STRAVA_REDIRECT_URI", "http://localhost:8124/strava/callback"),
        scope=["activity:read_all", "profile:read_all"],
    )
    return url


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8124)
```

**Step 3: Create Dockerfile**

Create `mcp/strava/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
EXPOSE 8124
CMD ["python", "server.py"]
```

**Step 4: Wire Strava MCP into health_agent**

In `agents/src/agents/health_agent/agent.py`, add MCP tools to fitness_coach:
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

def get_strava_tools():
    client = MultiServerMCPClient({
        "strava": {
            "transport": "http",
            "url": os.environ.get("STRAVA_MCP_URL", "http://localhost:8124/sse"),
        }
    })
    try:
        return asyncio.run(client.get_tools())
    except Exception as e:
        print(f"Warning: Strava MCP unavailable: {e}")
        return []

# In create_health_agent():
strava_tools = get_strava_tools()
fitness_coach = create_agent(model=model, tools=strava_tools, system_prompt=FITNESS_COACH_PROMPT)
```

**Step 5: Add to docker-compose.yml**

```yaml
  strava-mcp:
    build:
      context: ./mcp/strava
      dockerfile: Dockerfile
    ports:
      - "8124:8124"
    environment:
      - STRAVA_CLIENT_ID=${STRAVA_CLIENT_ID}
      - STRAVA_CLIENT_SECRET=${STRAVA_CLIENT_SECRET}
      - STRAVA_REDIRECT_URI=${STRAVA_REDIRECT_URI:-http://localhost:8124/strava/callback}
      - STRAVA_TOKEN_PATH=/data/strava_token.json
    volumes:
      - strava_data:/data
    networks:
      - copilotkit-network
```

Also add to the `agent` service environment:
```yaml
      - STRAVA_MCP_URL=http://strava-mcp:8124/sse
```

And add volume:
```yaml
volumes:
  openmemory_data:
    driver: local
  strava_data:
    driver: local
```

**Step 6: Verify Strava MCP starts**
```bash
cd mcp/strava && pip install -r requirements.txt && python server.py
# Expected: Uvicorn running on http://0.0.0.0:8124
# Check: curl http://localhost:8124/sse
```

**Step 7: Commit**
```bash
git add mcp/strava/ docker-compose.yml agents/src/agents/health_agent/agent.py
git commit -m "feat: build custom Strava MCP server and wire into fitness_coach sub-agent"
```

---

## Phase 3: AG-UI Shared State Schema

### Task 7: Define typed state schemas and enforce scope per agent

**Files:**
- Create: `agents/src/state.py`
- Modify: `agents/src/agents/exec_func_coach/agent.py`
- Modify: `agents/src/agents/personal_assistant/agent.py`
- Modify: `agents/src/agents/health_agent/agent.py`

**Step 1: Create shared state schema**

Create `agents/src/state.py`:
```python
"""Shared AG-UI state schema — each agent owns one slice"""

from typing import TypedDict, Optional
from dataclasses import dataclass, field


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
```

**Step 2: Add CopilotKit state sync to exec_func_coach**

In `agents/src/agents/exec_func_coach/agent.py`, update to use CopilotKit state:
```python
from copilotkit.langgraph import CopilotKitState, copilotkit_emit_state
from src.state import ZStyleState

# The agent reads/writes vision_board only
# Other slices are read-only for context
```

**Step 3: Commit**
```bash
git add agents/src/state.py
git commit -m "feat: define typed AG-UI state schema with strict per-agent ownership"
```

---

## Phase 4: Automations

### Task 8: Add APScheduler for background cron automations

**Files:**
- Create: `agents/src/scheduler.py`
- Modify: `agents/main.py`
- Add to `agents/requirements.txt`: `apscheduler>=3.10.0`

**Step 1: Add dependency**

In `agents/requirements.txt`:
```
apscheduler>=3.10.0
```

Run: `cd agents && uv pip install -r requirements.txt`

**Step 2: Create scheduler.py**

```python
"""Background automation scheduler using APScheduler"""

import os
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


LANGGRAPH_URL = os.environ.get("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")


async def run_agent_task(assistant_id: str, message: str):
    """Programmatically invoke a LangGraph agent"""
    from langgraph_sdk import get_client
    client = get_client(url=LANGGRAPH_URL)
    await client.runs.create(
        thread_id=None,
        assistant_id=assistant_id,
        input={"messages": [{"role": "user", "content": message}]},
    )


def daily_email_triage():
    """8am daily: summarize inbox and flag action items"""
    asyncio.run(run_agent_task(
        "personal_assistant",
        "Run daily email triage: fetch recent emails, create digest summary, flag action items. Update the emails state."
    ))


def weekly_calendar_plan():
    """Sunday 6pm: time-block the coming week"""
    asyncio.run(run_agent_task(
        "personal_assistant",
        "Run weekly calendar planning: review user goals, create time-blocks for the coming week optimized toward their lifestyle goals. Update calendar state."
    ))


def weekly_fitness_review():
    """Sunday 8pm: pull Strava stats and adjust workout plan"""
    asyncio.run(run_agent_task(
        "health_agent",
        "Run weekly fitness review: fetch latest Strava activity data, analyze performance trends, adjust next week's workout plan toward user goals. Update fitness state."
    ))


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        daily_email_triage,
        CronTrigger(hour=8, minute=0),
        id="daily_email_triage",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_calendar_plan,
        CronTrigger(day_of_week="sun", hour=18, minute=0),
        id="weekly_calendar_plan",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_fitness_review,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="weekly_fitness_review",
        replace_existing=True,
    )

    scheduler.start()
    print("Automation scheduler started: 3 V1 automations active")
    return scheduler
```

**Step 3: Start scheduler from main.py**

```python
"""Main entry point — three agent endpoints + automation scheduler"""

from src.agents import create_exec_func_coach_agent, create_personal_assistant_agent, create_health_agent
from src.scheduler import start_scheduler

exec_func_coach_graph = create_exec_func_coach_agent()
personal_assistant_graph = create_personal_assistant_agent()
health_agent_graph = create_health_agent()

# Start background automations
_scheduler = start_scheduler()
```

**Step 4: Verify scheduler starts**
```bash
cd agents && uv run python -c "from src.scheduler import start_scheduler; s = start_scheduler(); print('Jobs:', s.get_jobs())"
# Expected: Jobs: [daily_email_triage, weekly_calendar_plan, weekly_fitness_review]
```

**Step 5: Commit**
```bash
git add agents/src/scheduler.py agents/main.py agents/requirements.txt
git commit -m "feat: add APScheduler with 3 V1 automations (email triage, calendar plan, fitness review)"
```

---

## Phase 5: Frontend Restructure

### Task 9: Restructure layout — canvas left, chat right, 3-tab nav

**Files:**
- Modify: `frontend/src/components/example-layout/index.tsx`
- Create: `frontend/src/components/tab-nav/index.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/api/copilotkit/route.ts`

**Step 1: Create TabNav component**

Create `frontend/src/components/tab-nav/index.tsx`:
```tsx
"use client";

export type AgentTab = "coach" | "personal_assistant" | "health";

interface TabNavProps {
  activeTab: AgentTab;
  onTabChange: (tab: AgentTab) => void;
}

const TABS: { id: AgentTab; label: string; icon: string }[] = [
  { id: "coach", label: "Coach", icon: "🎯" },
  { id: "personal_assistant", label: "Personal Assistant", icon: "📋" },
  { id: "health", label: "Health", icon: "💪" },
];

export function TabNav({ activeTab, onTabChange }: TabNavProps) {
  return (
    <div className="flex border-b border-gray-200 bg-white px-4">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          <span>{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
```

**Step 2: Rewrite example-layout**

Replace `frontend/src/components/example-layout/index.tsx`:
```tsx
"use client";

import { useState } from "react";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { TabNav, AgentTab } from "@/components/tab-nav";
import { CoachCanvas } from "@/components/canvas/coach-canvas";
import { PersonalAssistantCanvas } from "@/components/canvas/personal-assistant-canvas";
import { HealthCanvas } from "@/components/canvas/health-canvas";
import { useFrontendTool } from "@copilotkit/react-core";

const AGENT_GRAPH_IDS: Record<AgentTab, string> = {
  coach: "exec_func_coach",
  personal_assistant: "personal_assistant",
  health: "health_agent",
};

export function AppLayout() {
  const [activeTab, setActiveTab] = useState<AgentTab>("coach");

  // Frontend tool: exec_func_coach can switch tabs
  useFrontendTool({
    name: "switchTab",
    description: "Switch the active tab to redirect user to a specialized agent. Use when the user's request is out of scope for the current agent.",
    parameters: { tab: { type: "string", enum: ["coach", "personal_assistant", "health"] } },
    handler: async ({ tab }: { tab: AgentTab }) => setActiveTab(tab),
  });

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="flex flex-1 overflow-hidden">
        {/* Canvas — left 2/3 */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === "coach" && <CoachCanvas />}
          {activeTab === "personal_assistant" && <PersonalAssistantCanvas />}
          {activeTab === "health" && <HealthCanvas />}
        </div>
        {/* Chat — right 1/3 */}
        <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
          <CopilotChat
            key={activeTab} // remount chat when tab changes
            agentId={AGENT_GRAPH_IDS[activeTab]}
          />
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Update page.tsx**

```tsx
"use client";

import { AppLayout } from "@/components/example-layout";
import { useExampleSuggestions } from "@/hooks";

export default function HomePage() {
  useExampleSuggestions();
  return <AppLayout />;
}
```

**Step 4: Update CopilotKit route to support multiple agents**

Replace `frontend/src/app/api/copilotkit/route.ts`:
```typescript
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const LANGGRAPH_URL = process.env.LANGGRAPH_DEPLOYMENT_URL || "http://localhost:8123";
const LANGSMITH_KEY = process.env.LANGSMITH_API_KEY || "";

function makeAgent(graphId: string) {
  return new LangGraphAgent({
    deploymentUrl: LANGGRAPH_URL,
    graphId,
    langsmithApiKey: LANGSMITH_KEY,
  });
}

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    endpoint: "/api/copilotkit",
    serviceAdapter: new ExperimentalEmptyAdapter(),
    runtime: new CopilotRuntime({
      agents: {
        exec_func_coach: makeAgent("exec_func_coach"),
        personal_assistant: makeAgent("personal_assistant"),
        health_agent: makeAgent("health_agent"),
      },
    }),
  });
  return handleRequest(req);
};
```

**Step 5: Verify frontend builds**
```bash
cd frontend && pnpm build
# Expected: Build succeeds, no TypeScript errors
```

**Step 6: Commit**
```bash
git add frontend/src/
git commit -m "feat: restructure frontend — canvas left, chat right, 3-tab agent navigation"
```

---

### Task 10: Build Coach canvas (vision board)

**Files:**
- Create: `frontend/src/components/canvas/coach-canvas.tsx`
- Create: `frontend/src/components/canvas/cards/goal-card.tsx`
- Create: `frontend/src/components/canvas/cards/habit-card.tsx`

**Step 1: Create goal-card.tsx**

```tsx
interface GoalCardProps {
  goal: { id: string; title: string; description: string; category: string; progress: number };
}

export function GoalCard({ goal }: GoalCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-900 text-sm">{goal.title}</h3>
        <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">{goal.category}</span>
      </div>
      <p className="text-xs text-gray-500 mb-3">{goal.description}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${goal.progress}%` }} />
        </div>
        <span className="text-xs text-gray-500">{goal.progress}%</span>
      </div>
    </div>
  );
}
```

**Step 2: Create habit-card.tsx**

```tsx
interface HabitCardProps {
  habit: { id: string; title: string; frequency: string; streak: number; completed_today: boolean };
  onToggle: (id: string) => void;
}

export function HabitCard({ habit, onToggle }: HabitCardProps) {
  return (
    <div className={`bg-white rounded-xl border p-3 flex items-center gap-3 ${
      habit.completed_today ? "border-green-200 bg-green-50" : "border-gray-100"
    }`}>
      <button
        onClick={() => onToggle(habit.id)}
        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
          habit.completed_today ? "bg-green-500 border-green-500 text-white" : "border-gray-300"
        }`}
      >
        {habit.completed_today && "✓"}
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{habit.title}</p>
        <p className="text-xs text-gray-500">{habit.frequency} · 🔥 {habit.streak} day streak</p>
      </div>
    </div>
  );
}
```

**Step 3: Create coach-canvas.tsx**

```tsx
"use client";

import { useAgent } from "@copilotkit/react-core";
import { GoalCard } from "./cards/goal-card";
import { HabitCard } from "./cards/habit-card";

export function CoachCanvas() {
  const { agent } = useAgent();
  const visionBoard = agent.state?.vision_board ?? { goals: [], habits: [], lifestyle_theme: "My Lifestyle" };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{visionBoard.lifestyle_theme}</h1>
        <p className="text-gray-500 text-sm mt-1">Your personalized lifestyle vision board</p>
      </div>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Goals</h2>
        {visionBoard.goals.length === 0 ? (
          <div className="text-center py-8 text-gray-400 border-2 border-dashed rounded-xl">
            Tell your Coach to set up your first goals
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {visionBoard.goals.map((goal: any) => <GoalCard key={goal.id} goal={goal} />)}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Daily Habits</h2>
        <div className="space-y-2">
          {visionBoard.habits.map((habit: any) => (
            <HabitCard
              key={habit.id}
              habit={habit}
              onToggle={(id) => {
                const updated = visionBoard.habits.map((h: any) =>
                  h.id === id ? { ...h, completed_today: !h.completed_today } : h
                );
                agent.setState({ vision_board: { ...visionBoard, habits: updated } });
              }}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
```

**Step 4: Commit**
```bash
git add frontend/src/components/canvas/coach-canvas.tsx frontend/src/components/canvas/cards/
git commit -m "feat: build Coach tab canvas — goals cards and habits tracker"
```

---

### Task 11: Build Personal Assistant canvas

**Files:**
- Create: `frontend/src/components/canvas/personal-assistant-canvas.tsx`

```tsx
"use client";

import { useAgent } from "@copilotkit/react-core";

export function PersonalAssistantCanvas() {
  const { agent } = useAgent();
  const pa = agent.state?.personal_assistant ?? { calendar: [], emails: [], tasks: [], automations: [] };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Personal Assistant</h1>

      {/* Email Digest */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Email Digest</h2>
        <div className="space-y-2">
          {pa.emails.length === 0 ? (
            <EmptyState message="No email digest yet — ask your assistant to triage your inbox" />
          ) : pa.emails.map((email: any) => (
            <div key={email.id} className="bg-white rounded-xl border border-gray-100 p-4">
              <div className="flex items-start justify-between">
                <p className="text-sm font-medium text-gray-900">{email.subject}</p>
                {email.action_required && (
                  <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full flex-shrink-0 ml-2">Action</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">{email.from_address}</p>
              <p className="text-xs text-gray-600 mt-2">{email.summary}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Calendar Blocks */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">This Week</h2>
        <div className="space-y-2">
          {pa.calendar.length === 0 ? (
            <EmptyState message="No time blocks yet — ask your assistant to plan your week" />
          ) : pa.calendar.map((block: any) => (
            <div key={block.id} className="bg-white rounded-xl border border-gray-100 p-3 flex items-center gap-3">
              <div className="w-1 h-10 bg-blue-400 rounded-full flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">{block.title}</p>
                <p className="text-xs text-gray-500">{block.start} → {block.end}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Automations */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Automations</h2>
        <div className="space-y-2">
          {pa.automations.map((auto: any) => (
            <div key={auto.id} className="bg-white rounded-xl border border-gray-100 p-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{auto.name}</p>
                <p className="text-xs text-gray-500">{auto.cron} · Last run: {auto.last_run ?? "Never"}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${auto.enabled ? "bg-green-50 text-green-600" : "bg-gray-100 text-gray-400"}`}>
                {auto.enabled ? "Active" : "Paused"}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-6 text-gray-400 border-2 border-dashed rounded-xl text-sm">{message}</div>
  );
}
```

**Commit:**
```bash
git add frontend/src/components/canvas/personal-assistant-canvas.tsx
git commit -m "feat: build Personal Assistant tab canvas — email digest, calendar blocks, automations"
```

---

### Task 12: Build Health canvas

**Files:**
- Create: `frontend/src/components/canvas/health-canvas.tsx`

```tsx
"use client";

import { useAgent } from "@copilotkit/react-core";
import { BarChart } from "@/components/generative-ui/charts/bar-chart";

export function HealthCanvas() {
  const { agent } = useAgent();
  const health = agent.state?.health ?? {
    weekly_plan: [], strava_stats: null, meal_plan: null, shopping_list: []
  };

  const stravaChartData = health.strava_stats ? [
    { label: "Recent Run (km)", value: health.strava_stats.recent_run_km },
    { label: "Recent Ride (km)", value: health.strava_stats.recent_ride_km },
    { label: "YTD Run (km)", value: health.strava_stats.ytd_run_km },
  ] : [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Health</h1>

      {/* Strava Stats */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Strava Stats</h2>
        {health.strava_stats ? (
          <BarChart title="Activity Summary" description="Your recent and year-to-date stats" data={stravaChartData} />
        ) : (
          <EmptyState message="Connect Strava to see your fitness stats" />
        )}
      </section>

      {/* Weekly Workout Plan */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Weekly Plan</h2>
        {health.weekly_plan.length === 0 ? (
          <EmptyState message="Ask your Fitness Coach to build your weekly workout plan" />
        ) : (
          <div className="grid grid-cols-7 gap-2">
            {health.weekly_plan.map((day: any) => (
              <div key={day.day} className="bg-white rounded-xl border border-gray-100 p-3 text-center">
                <p className="text-xs font-semibold text-gray-500 uppercase">{day.day.slice(0, 3)}</p>
                <p className="text-sm font-medium text-gray-900 mt-1">{day.workout_type}</p>
                <p className="text-xs text-gray-400 mt-1">{day.duration_min}min</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Meal Plan */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">This Week's Meals</h2>
        {!health.meal_plan ? (
          <EmptyState message="Ask your Nutritionist to create a meal plan" />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(health.meal_plan).map(([day, meals]: [string, any]) => (
              <div key={day} className="bg-white rounded-xl border border-gray-100 p-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{day}</p>
                {(meals as string[]).map((meal: string, i: number) => (
                  <p key={i} className="text-xs text-gray-700">• {meal}</p>
                ))}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-6 text-gray-400 border-2 border-dashed rounded-xl text-sm">{message}</div>
  );
}
```

**Commit:**
```bash
git add frontend/src/components/canvas/health-canvas.tsx
git commit -m "feat: build Health tab canvas — Strava stats chart, weekly workout plan, meal plan"
```

---

## Phase 6: Docker & Environment

### Task 13: Update docker-compose and environment variables

**Files:**
- Modify: `docker-compose.yml`
- Create: `.env.example`

**Step 1: Create .env.example**

```bash
# Required
GOOGLE_API_KEY=

# Optional
GEMINI_MODEL=gemini-2.0-flash
LANGSMITH_API_KEY=

# Strava (required for health agent)
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REDIRECT_URI=http://localhost:8124/strava/callback

# OAuth token paths (relative to agents/ dir)
GMAIL_TOKEN_PATH=gmail_token.json
CALENDAR_TOKEN_PATH=calendar_token.json
GOOGLE_CLIENT_SECRETS_PATH=credentials.json
```

**Step 2: Update agent service in docker-compose to include all new env vars**

In the `agent` service environment block, add:
```yaml
      - STRAVA_MCP_URL=http://strava-mcp:8124/sse
      - GMAIL_TOKEN_PATH=/app/agents/gmail_token.json
      - CALENDAR_TOKEN_PATH=/app/agents/calendar_token.json
      - GOOGLE_CLIENT_SECRETS_PATH=/app/agents/credentials.json
```

**Step 3: Full docker smoke test**
```bash
docker compose up --build
# Expected:
# - memory: healthy on :8080
# - strava-mcp: running on :8124
# - agent: healthy on :8123 (3 endpoints)
# - app: running on :3000
```

**Step 4: Commit**
```bash
git add docker-compose.yml .env.example
git commit -m "feat: update docker-compose with strava-mcp service and complete env config"
```

---

## Phase 7: End-to-End Verification

### Task 14: Manual smoke test checklist

Run each of these and verify:

```
[ ] pnpm dev + langgraph dev both start without errors
[ ] http://localhost:3000 loads with 3 tabs
[ ] Coach tab: chat connects to exec_func_coach endpoint
[ ] PA tab: chat connects to personal_assistant endpoint
[ ] Health tab: chat connects to health_agent endpoint
[ ] Say "plan my week" in Coach → exec_func_coach A2A delegates to personal_assistant
[ ] Coach tries to edit workout plan → it delegates to health_agent instead
[ ] Say "what did I do on Strava this week" in Health tab → fitness_coach uses Strava MCP
[ ] Say "triage my emails" in PA tab → email_manager uses GmailToolkit
[ ] Vision board updates in Coach tab when agent sets goals
[ ] switchTab frontend tool works: Coach can redirect to Health tab
[ ] docker compose up --build → all 4 services healthy
```

**Final commit:**
```bash
git add .
git commit -m "feat: ZStyle V1 complete — hierarchical MAS, A2A, OAuth (Gmail/Calendar/Strava), tabbed canvas"
```

---

## Resume Bullet Mapping

| Resume Bullet | Implemented By |
|---|---|
| Hierarchical MAS with LangGraph | Tasks 1–3 (exec_func_coach + PA + health, supervisor pattern) |
| A2A Protocol inter-agent comms | Task 3 (request_personal_assistant, request_health_agent tools) |
| OAuth 2.0 for Gmail, Calendar | Tasks 4–5 (GmailToolkit, CalendarToolkit, token files) |
| Event-driven FastAPI endpoint | LangGraph serves as the FastAPI layer; automations = event-driven |
| OpenMemory MCP long-term context | Already working, extended in exec_func_coach |
| Copilotkit AG-UI shared state | Tasks 7, 9–12 (typed state schema, per-agent canvas) |
| Custom MCP server (Strava) | Task 6 |
| Docker Compose orchestration | Task 13 (4-service compose: memory, strava-mcp, agent, app) |
| Full-stack Next.js + agent | Tasks 9–12 (tabbed canvas, dynamic agent connection per tab) |
| Structured JSON schema | Task 7 (TypedDict state schema, enforced per-agent writes) |

---

## V1.5 Backlog (after V1 ships)

- TickTick/Todoist integration → task_agent
- Walmart API → nutritionist shopping list
- Apple HealthKit → fitness_coach
- Recipe app integration → nutritionist
- Push notifications for automation completions

## V2 Backlog

- Postgres (Neon/Supabase) for multi-user session storage
- Session logging (5-min inactivity timeout → log to DB)
- Auth / user accounts
