# ZStyle Vision Document

> This document captures the full product vision and every design decision made for V1.
> Read this BEFORE reading the implementation plan. It is the source of truth for WHY.

---

## What ZStyle Is

ZStyle is a **lifestyle product**. We sell and market lifestyles — not productivity tools.

The interface is a **functional vision board**: a canvas where each section represents a pillar of the user's life, powered by specialized AI agents connected to real external apps. The user configures their lifestyle goals, habits, and automations, and the system works in the background to optimize toward them.

**Core loop:** User defines vision → Agents connect to apps → Automations run silently → Canvas reflects current state of life.

---

## Product Pillars (V1)

Three agent domains, each with its own canvas view and chat:

### 1. Coach (`exec_func_coach`)
- The user's primary AI companion and orchestrator
- Owns the vision board: goals, habits, lifestyle theme
- Has global authority over automations across all agents
- Uses patterns from the user's schedule/history to proactively optimize future plans
- Delegates EVERYTHING outside its scope via A2A — it never executes health or PA tasks itself

### 2. Personal Assistant (`personal_assistant`)
- Background agent — primarily invoked by the Coach via A2A, not directly by users
- Handles all productivity: email, calendar, tasks
- Sub-agents: `email_manager` (Gmail), `calendar_agent` (Google Calendar), `task_agent` (stub V1)
- Owns automation scheduling at the execution level
- Can refactor schedules when conflicts arise

### 3. Health Agent (`health_agent`)
- Owns all physical wellbeing data and plans
- Sub-agents: `fitness_coach` (Strava), `nutritionist` (stub V1)
- Fitness and nutrition work together — e.g., high-energy diet aligned with training load
- Neither Coach nor PA can write to health state directly

---

## Architecture Decisions

### Agent Scope Boundaries (NON-NEGOTIABLE)
Each agent owns exactly one slice of AG-UI shared state. **No agent writes to another agent's state slice — ever.**

- `exec_func_coach` writes to: `vision_board`
- `personal_assistant` writes to: `personal_assistant`
- `health_agent` writes to: `health`

The Coach can READ all state for context. But to change anything outside its slice, it MUST use A2A to request the owning agent to make the change. This is intentional — it enforces clean separation and makes the A2A protocol meaningful.

**Example:** Coach sees user hasn't been hitting workouts. It uses A2A to ask health_agent to adjust the plan. It does NOT write to `health.fitness` itself.

### A2A Protocol
- Top-level agents (`exec_func_coach`, `personal_assistant`, `health_agent`) are each separate LangGraph endpoints
- A2A is implemented as tool calls on the orchestrator: `request_personal_assistant(task)` and `request_health_agent(task)`
- Sub-agents (email_manager, calendar_agent, fitness_coach, etc.) are internal LangGraph nodes within their parent agent — they use the supervisor routing pattern, NOT A2A
- A2A is only between top-level agents

### Agent Framework
- Use `langchain.agents.create_agent` (NOT the deprecated `langgraph.prebuilt.create_react_agent`)
- LangGraph (`StateGraph`, `END`, conditional edges) is used for the supervisor routing pattern inside personal_assistant and health_agent
- CopilotKit's `CopilotKitMiddleware` is applied to `exec_func_coach` only (the user-facing agent)
- `system_prompt=` not `prompt=` is the correct parameter name for `create_agent`

### Automations
- Python `APScheduler` runs inside the agent server alongside LangGraph
- V1 automations: `daily_email_triage` (8am), `weekly_calendar_plan` (Sunday 6pm), `weekly_fitness_review` (Sunday 8pm)
- Automations are stored in `personal_assistant.automations` state (visible in PA canvas)
- Coach has global authority: can create, pause, delete automations via A2A to personal_assistant
- Coach uses automation run history + user schedule patterns to optimize future schedules
- Notifications are deferred to V1.5 — automations run silently and update canvas

### CopilotKit AG-UI State
- The single source of truth for canvas state in V1
- Each agent has a typed state slice (defined in `agents/src/state.py`)
- Canvas is purely reactive — reads state, renders it
- No separate database in V1 (that's V2 with Postgres/Neon/Supabase + multi-user)
- Session state lives in LangGraph's in-memory store per conversation
- Sessions are keyed 5-minute inactivity timeout (V2 feature — log to DB on expiry)

---

## Frontend Design Decisions

### Layout (EXACT)
```
┌──────────────────────────────────────────────────────────┐
│ [Coach] [Personal Assistant] [Health]   ← tab nav        │
├────────────────────────────┬─────────────────────────────┤
│  CANVAS  (left, 2/3)       │  CHAT  (right, 1/3)         │
│                            │                             │
│  Reacts to agent state     │  Talks to active tab's      │
│  Shows cards/charts/plans  │  LangGraph endpoint         │
└────────────────────────────┴─────────────────────────────┘
```

- **Canvas is LEFT, chat is RIGHT** — this is inverted from the original scaffold
- Each tab switch changes BOTH the canvas content AND which LangGraph endpoint the chat connects to
- The chat remounts (`key={activeTab}`) on tab change to get a fresh conversation with the new agent

### Per-Tab Agent Connections
| Tab | Canvas | Chat endpoint |
|-----|--------|---------------|
| Coach | Vision board (goals, habits, theme) | `exec_func_coach` |
| Personal Assistant | Email digest, calendar blocks, tasks, automations | `personal_assistant` |
| Health | Strava stats chart, weekly workout plan, meal plan | `health_agent` |

### Frontend Tools
- `switchTab(tab)` — exec_func_coach uses this to redirect user to the right agent when a request is out of its scope
- Agent says "let me connect you with your Personal Assistant" then calls `switchTab("personal_assistant")`
- Charts (bar, pie) already exist in `generative-ui/charts/` — reuse them in Health canvas

---

## OAuth & Integrations

### V1 Must-Have
| Service | Library | Auth Pattern |
|---------|---------|-------------|
| Gmail | `langchain-google-community` GmailToolkit | `get_gmail_credentials()` → `gmail_token.json` |
| Google Calendar | `langchain-google-community` CalendarToolkit | `get_google_credentials()` → `calendar_token.json` |
| Strava | Custom MCP server using `stravalib` | `strava_token.json` |

- All tokens stored as files in the agent container for V1 (single user)
- `credentials.json` downloaded from Google Cloud Console — NOT committed to git
- First run opens browser OAuth consent, subsequent runs use cached token
- Custom Strava MCP server is a real FastAPI/MCP server at port 8124

### V1.5 Nice-to-Have
TickTick/Todoist, Walmart API, Apple HealthKit, recipe app

### V2
Multi-user token storage in Postgres, user accounts, session logging

---

## Docker Services (V1)

| Service | Port | Purpose |
|---------|------|---------|
| `memory` | 8080 | OpenMemory MCP (SQLite + Gemini embeddings) |
| `strava-mcp` | 8124 | Custom Strava MCP server |
| `agent` | 8123 | LangGraph server (3 endpoints) |
| `app` | 3000 | Next.js frontend |

---

## Versioning Roadmap

| Version | Focus |
|---------|-------|
| **V1** | Core MAS, A2A, Gmail + Calendar + Strava, tabbed canvas |
| **V1.5** | TickTick, Walmart, HealthKit, recipe app, push notifications |
| **V2** | Postgres (Neon/Supabase), multi-user, session logging, auth |

---

## What NOT to Do

- Do NOT use `langgraph.prebuilt.create_react_agent` — it is deprecated
- Do NOT let exec_func_coach write to health or personal_assistant state directly
- Do NOT implement notifications in V1 — deferred to V1.5
- Do NOT implement multi-user or database in V1 — deferred to V2
- Do NOT use `prompt=` with `create_agent` — use `system_prompt=`
- Do NOT put CopilotKitMiddleware on personal_assistant or health_agent — only exec_func_coach is user-facing

---

## Resume Bullet Mapping

Every bullet on the resume maps to a real implementation:

| Bullet | Code |
|--------|------|
| "Hierarchical MAS with LangGraph" | 3 top-level graphs + supervisor pattern inside PA and health |
| "A2A Protocol inter-agent comms" | `request_personal_assistant()` and `request_health_agent()` tools on exec_func_coach |
| "OAuth 2.0 for Gmail, Calendar, TickTick" | GmailToolkit + CalendarToolkit token flows |
| "FastAPI event-driven endpoint" | LangGraph serves via FastAPI; automations = event-driven cron |
| "OpenMemory MCP long-term context" | Already working; extended in exec_func_coach |
| "Copilotkit AG-UI shared state" | Typed state schema, per-agent canvas views |
| "Custom MCP server" | Strava MCP server in `mcp/strava/` |
| "Docker Compose orchestration" | 4-service compose |
| "Structured JSON schema enforcement" | TypedDict state schema in `agents/src/state.py` |
